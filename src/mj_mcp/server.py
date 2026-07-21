"""Midjourney MCP Server — image and video generation via Discord self-bot.

Wraps Discord interaction layer as FastMCP tools for Universe bot integration.
Streamable HTTP transport with Bearer token auth. Auto-upscale: imagine()
returns 4 individual HD images, not a raw grid.
"""

import asyncio
import hashlib
import logging
import os
import sys
import time
from pathlib import Path
from typing import Annotated, Optional

# Load .env before anything else
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
        print(f"[MJ-MCP] Loaded .env from {_env_path}")
    else:
        print(f"[MJ-MCP] No .env found at {_env_path}")
except ImportError:
    print("[MJ-MCP] python-dotenv not installed -- relying on shell env")

from mcp.server.fastmcp import FastMCP, Context

# Monkey-patch FastMCP's DNS rebinding check
from mcp.server.transport_security import TransportSecurityMiddleware

_orig_validate = TransportSecurityMiddleware.validate_request
async def _patched_validate(self, request, is_post=False):
    return None

TransportSecurityMiddleware.validate_request = _patched_validate

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BEARER_TOKEN = os.environ.get("DESIGNER_MCP_TOKEN", "")
if BEARER_TOKEN:
    print(f"[MJ-MCP] Auth enabled (token: {BEARER_TOKEN[:8]}...)")
else:
    print("[MJ-MCP] WARNING: Auth DISABLED -- open access")

DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN", "")
MJ_CHANNEL_ID = os.environ.get("MJ_CHANNEL_ID", "")
MJ_MAX_CONCURRENT = int(os.environ.get("MJ_MAX_CONCURRENT_JOBS", "3"))
GENERATION_TIMEOUT = int(os.environ.get("GENERATION_TIMEOUT_SECONDS", "40"))
UPSCALE_TIMEOUT = int(os.environ.get("UPSCALE_TIMEOUT_SECONDS", "15"))
TOTAL_TIMEOUT = int(os.environ.get("TOTAL_TIMEOUT_SECONDS", "55"))

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8005"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("mj-mcp")

# ---------------------------------------------------------------------------
# Discord client + task tracker
# ---------------------------------------------------------------------------

from mj_mcp.discord.interaction import InteractionClient
from mj_mcp.discord.gateway import GatewayMonitor
from mj_mcp.discord import correlation as mj_correl
from mj_mcp.tracker import TaskTracker

tracker = TaskTracker()
interaction: InteractionClient | None = None
gateway: GatewayMonitor | None = None

# Readiness: becomes True once gateway connects
_ready: bool = False
_ready_event: asyncio.Event = asyncio.Event()
_start_time: float = time.time()

# Dedup: prompt_hash -> task_id for in-flight imagine calls
_in_flight: dict[str, str] = {}
_in_flight_lock: asyncio.Lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("midjourney")

# Health endpoint — no auth required (excluded by BearerAuthMiddleware)
from starlette.responses import JSONResponse as _JSONResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request):
    return _JSONResponse({
        "status": "ok" if _ready else "warming",
        "gateway_connected": _ready,
        "uptime_seconds": int(time.time() - _start_time),
    })

# ---- Tool helpers --------------------------------------------------------


async def _send_imagine(prompt: str, aspect_ratio: str) -> str | None:
    """Send /imagine, wait for grid, auto-upscale U1-U4, return task id.

    Deduplicates: if the same prompt is already in-flight, waits for that task.
    """
    if not interaction:
        raise RuntimeError("Discord client not initialized")

    # Dedup: check if this prompt is already being generated
    prompt_key = hashlib.sha256(f"{prompt}|{aspect_ratio}".encode()).hexdigest()
    async with _in_flight_lock:
        existing_id = _in_flight.get(prompt_key)
    if existing_id:
        existing = await tracker.get_task(existing_id)
        if existing and existing.status.value not in ("completed", "failed"):
            logger.info("Dedup: joining existing task %s for prompt %s", existing_id, prompt[:40])
            # Wait for existing task
            try:
                await asyncio.wait_for(existing.complete_event.wait(), timeout=GENERATION_TIMEOUT + UPSCALE_TIMEOUT)
            except asyncio.TimeoutError:
                pass
            return existing_id

    state = await tracker.create_task(prompt, aspect_ratio)
    async with _in_flight_lock:
        _in_flight[prompt_key] = state.id

    # Rate limit: minimum 3s between fresh imagine calls
    wait_time = mj_correl.check_rate_limit()
    if wait_time:
        logger.info("Rate limit: waiting %.1fs before next imagine", wait_time)
        await asyncio.sleep(wait_time)
    mj_correl.update_last_imagine_time()

    # Set as current task for gateway message routing
    mj_correl.set_current(state.id)

    # Send prompt as-is — no tags, no injection
    final_prompt = f"{prompt} --ar {aspect_ratio}" if aspect_ratio != "1:1" else prompt
    status = await interaction.send_imagine(final_prompt)
    if status not in (200, 204):
        interaction.invalidate_command_cache()
        await asyncio.sleep(1)
        status = await interaction.send_imagine(final_prompt)
        if status not in (200, 204):
            await tracker.set_failed(state.id, f"Discord returned HTTP {status}")
            return None

    # Wait for grid (4-image grid with U1-U4 buttons)
    try:
        await asyncio.wait_for(state.grid_event.wait(), timeout=GENERATION_TIMEOUT)
    except asyncio.TimeoutError:
        await tracker.set_failed(state.id, "Generation timed out")

    # Check if grid arrived (if failed, don't try to upscale)
    current = await tracker.get_task(state.id)
    if not current or current.status.value == "failed":
        return state.id

    # Start upscale phase: click U1-U4 asynchronously
    if current.upscale_buttons:
        await tracker.start_upscale_phase(state.id, count=4)
        asyncio.create_task(_fire_upscales(state.id))

        # Poll for upscale results — respect total timeout (Universe = 60s)
        elapsed = time.time() - state.created_at
        remaining = max(10, TOTAL_TIMEOUT - elapsed)
        deadline = time.time() + remaining
        while time.time() < deadline:
            await asyncio.sleep(3)
            current = await tracker.get_task(state.id)
            if not current:
                break
            if len(current.upscale_results) >= 4:
                await tracker.set_complete(
                    state.id,
                    [current.upscale_results[i] for i in range(1, 5)],
                )
                break

        # After timeout, return whatever we have
        current = await tracker.get_task(state.id)
        if current and current.status.value != "completed":
            if current.upscale_results:
                urls = [current.upscale_results.get(i, current.grid_url) for i in range(1, 5)]
                await tracker.set_complete(state.id, urls)
            else:
                await tracker.set_failed(state.id, "Upscale timed out with no results")

    # Cleanup dedup entry
    async with _in_flight_lock:
        if _in_flight.get(prompt_key) == state.id:
            _in_flight.pop(prompt_key, None)

    return state.id


async def _fire_upscales(task_id: str) -> None:
    """Click U1, U2, U3, U4 buttons for a completed grid."""
    if not interaction:
        return
    state = await tracker.get_task(task_id)
    if not state or not state.message_id:
        return

    for i in range(1, 5):
        custom_id = state.upscale_buttons.get(i)
        if not custom_id:
            continue
        await asyncio.sleep(0.5)  # Small delay between clicks
        try:
            await interaction.send_component_interaction(state.message_id, custom_id)
        except Exception as e:
            logger.warning("Failed to send upscale U%d for %s: %s", i, task_id, e)


async def _click_and_wait(
    message_id: str, custom_id: str, prompt: str, aspect_ratio: str,
) -> str | None:
    """Click a button and wait for the new result. Returns new task id."""
    if not interaction:
        raise RuntimeError("Discord client not initialized")

    status = await interaction.send_component_interaction(message_id, custom_id)
    if status not in (200, 204):
        return None

    new_state = await tracker.create_task(prompt, aspect_ratio)
    mj_correl.set_current(new_state.id)

    try:
        await asyncio.wait_for(new_state.complete_event.wait(), timeout=GENERATION_TIMEOUT)
    except asyncio.TimeoutError:
        await tracker.set_failed(new_state.id, "Action timed out")

    return new_state.id


async def _task_result(task_id: str | None) -> dict:
    if not task_id:
        return {"error": "Failed to create task"}
    state = await tracker.get_task(task_id)
    return tracker.to_result(state) if state else {"error": "Task not found"}


# ---- Tool: imagine -------------------------------------------------------


@mcp.tool()
async def imagine(
    prompt: Annotated[str, "Text description of the image to generate"],
    aspect_ratio: Annotated[str, "Aspect ratio (e.g. 1:1, 16:9, 9:16, 4:3, 3:4)"] = "1:1",
) -> dict:
    """Generate 4 HD images from a text prompt using Midjourney.

    Returns grid overview + 4 individual HD image URLs.
    Synchronous — blocks until ready (up to 55s).
    Use vary() for variations, animate() for video.
    """
    task_id = await _send_imagine(prompt, aspect_ratio)
    return await _task_result(task_id)


# ---- Tool: upscale -------------------------------------------------------


@mcp.tool()
async def upscale(
    index: Annotated[int, "Which image to upscale (1-4): 1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right"],
    task_id: Annotated[str | None, "Task ID from imagine(). If omitted, uses most recent."] = None,
) -> dict:
    """Manually upscale one image from a grid (usually not needed — imagine auto-upscales).
    """
    if index < 1 or index > 4:
        return {"error": "Index must be 1-4"}

    if not task_id:
        task_id = tracker.get_most_recent_task_id()
        if not task_id:
            return {"error": "No recent generation found"}

    state = await tracker.get_task(task_id)
    if not state:
        return {"error": f"Task {task_id} not found"}
    if not state.message_id or index not in state.upscale_buttons:
        return {"error": f"No upscale button for index {index}"}

    new_id = await _click_and_wait(
        state.message_id,
        state.upscale_buttons[index],
        f"upscale {index}: {state.prompt}",
        state.aspect_ratio,
    )
    return await _task_result(new_id)


# ---- Tool: vary ----------------------------------------------------------


@mcp.tool()
async def vary(
    index: Annotated[int, "Which image to vary (1-4): 1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right"],
    task_id: Annotated[str | None, "Task ID from imagine(). If omitted, uses most recent."] = None,
) -> dict:
    """Generate variations of one image from a grid.
    """
    if not task_id:
        task_id = tracker.get_most_recent_task_id()
        if not task_id:
            return {"error": "No recent generation found"}
    if index < 1 or index > 4:
        return {"error": "Index must be 1-4"}

    state = await tracker.get_task(task_id)
    if not state:
        return {"error": f"Task {task_id} not found"}

    vary_cid = f"MJ::JOB::variation::{index}::"
    for label, cid in state.all_buttons.items():
        if "variation" in cid.lower() and str(index) in cid:
            vary_cid = cid
            break

    new_id = await _click_and_wait(
        state.message_id, vary_cid,
        f"variation {index}: {state.prompt}",
        state.aspect_ratio,
    )
    return await _task_result(new_id)


# ---- Tool: reroll --------------------------------------------------------


@mcp.tool()
async def reroll(task_id: Annotated[str | None, "Task ID from imagine(). If omitted, uses most recent."] = None) -> dict:
    """Regenerate with the same prompt (reroll).
    """
    if not task_id:
        task_id = tracker.get_most_recent_task_id()
        if not task_id:
            return {"error": "No recent generation found"}
    state = await tracker.get_task(task_id)
    if not state:
        return {"error": "Task not found"}

    reroll_cid = "MJ::JOB::reroll::0::"
    for label, cid in state.all_buttons.items():
        if "reroll" in cid.lower():
            reroll_cid = cid
            break

    new_id = await _click_and_wait(
        state.message_id, reroll_cid,
        f"reroll: {state.prompt}",
        state.aspect_ratio,
    )
    return await _task_result(new_id)


# ---- Tool: animate (video) -----------------------------------------------


@mcp.tool()
async def animate(
    task_id: Annotated[str | None, "Task ID from imagine(). If omitted, uses the most recent generation."] = None,
    image_index: Annotated[int | None, "Which image to animate (1-4): 1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right"] = None,
    motion: Annotated[str, "Motion level: low or high"] = "low",
) -> dict:
    """Animate a generated image into a short video.

    Uses the most recent generation if task_id is omitted.
    image_index selects which of the 4 images to animate (1-4 grid position).
    """
    # If no task_id, use the most recent completed task
    if not task_id:
        task_id = tracker.get_most_recent_task_id()
        if not task_id:
            return {"error": "No recent generation found. Call imagine() first."}
        logger.info("Animate: using most recent task %s", task_id[:8])

    state = await tracker.get_task(task_id)
    if not state:
        return {"error": f"Task not found"}

    # If image_index given, look up the actual animate button from stored upscale buttons
    if image_index is not None:
        msg_id = state.upscale_message_ids.get(image_index)
        upscale_btns = state.upscale_result_buttons.get(image_index, {})
        if msg_id and upscale_btns:
            # Find the actual animate button by label
            animate_cid = None
            for label, cid in upscale_btns.items():
                if "animate" in label.lower() or "video" in label.lower():
                    # Prefer the motion level requested
                    if motion.lower() in label.lower():
                        animate_cid = cid
                        break
                    if not animate_cid:
                        animate_cid = cid
            if animate_cid:
                logger.info("Animate: clicking button '%s' on msg %s", animate_cid[:40], msg_id)
                status = await interaction.send_component_interaction(msg_id, animate_cid)
                if status in (200, 204):
                    new_id = await tracker.create_task(
                        f"animate img{image_index}: {state.prompt}",
                        state.aspect_ratio,
                    )
                    mj_correl.set_current(new_id.id)
                    try:
                        await asyncio.wait_for(new_id.complete_event.wait(), timeout=GENERATION_TIMEOUT)
                    except asyncio.TimeoutError:
                        await tracker.set_failed(new_id.id, "Animation timed out")
                    return await _task_result(new_id.id)
                else:
                    return {"error": f"Animate interaction failed: HTTP {status}"}
            else:
                return {"error": f"No animate button found on image {image_index}. Available: {list(upscale_btns.keys())}"}
        else:
            return {"error": f"No tracked upscale message for image {image_index}"}

    # Fallback: look for animate on grid message
    animate_cid = None
    for label, cid in state.all_buttons.items():
        if "animate" in label.lower() or "animate" in cid.lower() or "video" in cid.lower():
            animate_cid = cid
            break

    if animate_cid:
        new_id = await _click_and_wait(
            state.message_id, animate_cid,
            f"animate: {state.prompt}",
            state.aspect_ratio,
        )
        return await _task_result(new_id)

    prompt = f"{state.prompt} --animate"
    new_id = await _send_imagine(prompt, state.aspect_ratio)
    return await _task_result(new_id)


# ---- Callbacks: wire gateway events to tracker ---------------------------


async def _on_grid_complete(
    task_id: str, image_url: str,
    message_id: str, upscale_buttons: dict, all_buttons: dict,
    has_animate: bool, **kwargs,
):
    # Don't re-process grid if already set
    state = await tracker.get_task(task_id)
    if state and state.grid_url:
        return
    logger.info("Grid complete: task=%s buttons=%s msg=%s", task_id[:8], list(upscale_buttons.keys()), message_id)
    await tracker.set_grid_complete(
        task_id, image_url, message_id,
        upscale_buttons, all_buttons, has_animate,
    )


async def _on_single_complete(
    task_id: str, image_urls: list[str], message_id: str, all_buttons: dict | None = None, **kwargs,
):
    """Handle a single image result — could be an upscale or direct complete."""
    state = await tracker.get_task(task_id)
    if state and state.status.value in ("upscaling", "grid_complete"):
        url = image_urls[0] if image_urls else ""
        if url:
            for i in range(1, 5):
                if i not in state.upscale_results:
                    logger.info("Upscale result: task=%s index=%d url=%.60s buttons=%s", task_id[:8], i, url, list(all_buttons.keys()) if all_buttons else [])
                    await tracker.record_upscale_result(task_id, i, url, message_id, all_buttons)
                    return
    logger.info("Single complete (non-upscale): task=%s urls=%d", task_id[:8], len(image_urls))
    await tracker.set_complete(task_id, image_urls)


async def _on_video_complete(
    task_id: str, video_url: str, **kwargs,
):
    await tracker.set_video_complete(task_id, video_url)


async def _on_progress(task_id: str, progress: int, **kwargs):
    await tracker.update_progress(task_id, progress)


async def _on_gateway_ready():
    """Called when the Discord gateway connects successfully."""
    global _ready
    _ready = True
    _ready_event.set()
    logger.info("MCP ready: gateway connected, accepting tool calls")


# ---- Lifespan: start/stop Discord connections ----------------------------


async def start_backend():
    global interaction, gateway, _semaphore

    if not DISCORD_USER_TOKEN or not MJ_CHANNEL_ID:
        logger.warning("DISCORD_USER_TOKEN or MJ_CHANNEL_ID not set -- mock mode")
        return

    _semaphore = asyncio.Semaphore(MJ_MAX_CONCURRENT)

    interaction = InteractionClient(
        user_token=DISCORD_USER_TOKEN,
        channel_id=MJ_CHANNEL_ID,
    )
    await interaction.start()

    if DISCORD_BOT_TOKEN:
        gateway = GatewayMonitor(
            bot_token=DISCORD_BOT_TOKEN,
            channel_id=int(MJ_CHANNEL_ID),
        )
        gateway.set_callbacks(
            on_progress=_on_progress,
            on_grid_complete=_on_grid_complete,
            on_single_complete=_on_single_complete,
            on_video_complete=_on_video_complete,
            on_ready=_on_gateway_ready,
        )

        async def _run_gateway():
            try:
                logger.info("Gateway connecting to Discord...")
                await gateway.start()
            except Exception as e:
                logger.error("Gateway connection failed: %s", e, exc_info=True)

        asyncio.create_task(_run_gateway())
    else:
        logger.warning("No DISCORD_BOT_TOKEN -- gateway disabled")

    logger.info("MJ-MCP ready: channel=%s, max_concurrent=%d", MJ_CHANNEL_ID, MJ_MAX_CONCURRENT)


async def stop_backend():
    global interaction, gateway
    if gateway:
        await gateway.stop()
    if interaction:
        await interaction.stop()
    logger.info("MJ-MCP shutdown")
