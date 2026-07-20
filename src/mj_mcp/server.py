"""Midjourney MCP Server — image and video generation via Discord self-bot.

Wraps Discord interaction layer as FastMCP tools for Universe bot integration.
Streamable HTTP transport with Bearer token auth. Auto-upscale: imagine()
returns 4 individual HD images, not a raw grid.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

# Load .env before anything else
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent / ".env"
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
GENERATION_TIMEOUT = int(os.environ.get("GENERATION_TIMEOUT_SECONDS", "180"))
UPSCALE_TIMEOUT = int(os.environ.get("UPSCALE_TIMEOUT_SECONDS", "120"))

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
from mj_mcp.discord.correlation import CorrelationManager
from mj_mcp.tracker import TaskTracker

correlation = CorrelationManager()
tracker = TaskTracker()
interaction: InteractionClient | None = None
gateway: GatewayMonitor | None = None
_semaphore: asyncio.Semaphore | None = None

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("midjourney")

# ---- Tool helpers --------------------------------------------------------


async def _send_imagine(prompt: str, aspect_ratio: str) -> str | None:
    """Send /imagine, wait for grid, auto-upscale U1-U4, return task id."""
    if not interaction:
        raise RuntimeError("Discord client not initialized")

    state = await tracker.create_task(prompt, aspect_ratio)
    tag = correlation.generate_tag()
    await tracker.set_correlation(state.id, tag)
    correlation.register(tag, state.id)

    tagged = correlation.embed_in_prompt(prompt, tag)
    if aspect_ratio != "1:1":
        tagged = f"{tagged} --ar {aspect_ratio}"

    status = await interaction.send_imagine(tagged)
    if status not in (200, 204):
        interaction.invalidate_command_cache()
        await asyncio.sleep(1)
        status = await interaction.send_imagine(tagged)
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
        # Fire upscale interactions in background
        asyncio.create_task(_fire_upscales(state.id))

        # Wait for all upscales to complete
        try:
            await asyncio.wait_for(current.upscale_event.wait(), timeout=UPSCALE_TIMEOUT)
        except asyncio.TimeoutError:
            # Log partial results — whatever we got is better than grid
            current = await tracker.get_task(state.id)
            if current and current.upscale_results:
                urls = [current.upscale_results.get(i, current.grid_url) for i in range(1, 5)]
                await tracker.set_complete(state.id, urls)
            else:
                await tracker.set_failed(state.id, "Upscale timed out with no results")

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
    tag = correlation.generate_tag()
    await tracker.set_correlation(new_state.id, tag)
    correlation.register(tag, new_state.id)

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
async def imagine(prompt: str, aspect_ratio: str = "1:1") -> dict:
    """Generate 4 HD images from a text prompt using Midjourney.

    Auto-upscales: returns 4 individual HD image URLs, not a grid.
    Use vary() for variations, animate() for video.

    Args:
        prompt: Text description of the image to generate
        aspect_ratio: Aspect ratio (e.g. 1:1, 16:9, 9:16, 4:3, 3:4)
    """
    task_id = await _send_imagine(prompt, aspect_ratio)
    return await _task_result(task_id)


# ---- Tool: wait ----------------------------------------------------------


@mcp.tool()
async def wait(task_id: str) -> dict:
    """Wait for a task to complete and return latest status.

    Args:
        task_id: Task ID from imagine() or other tool
    """
    state = await tracker.get_task(task_id)
    if not state:
        return {"error": f"Task {task_id} not found"}

    if state.status.value in ("completed", "failed"):
        return tracker.to_result(state)

    remaining = max(1, GENERATION_TIMEOUT - (time.time() - state.created_at))
    try:
        await asyncio.wait_for(state.complete_event.wait(), timeout=remaining)
    except asyncio.TimeoutError:
        pass

    state = await tracker.get_task(task_id)
    return tracker.to_result(state) if state else {"error": "Task not found"}


# ---- Tool: upscale -------------------------------------------------------


@mcp.tool()
async def upscale(task_id: str, index: int) -> dict:
    """Manually upscale one image from a grid (usually not needed — imagine auto-upscales).

    Args:
        task_id: Task ID from imagine() result
        index: Which image to upscale (1-4)
    """
    if index < 1 or index > 4:
        return {"error": "Index must be 1-4"}

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
async def vary(task_id: str, index: int) -> dict:
    """Generate variations of one image from a grid.

    Args:
        task_id: Task ID from imagine() result
        index: Which image to vary (1-4)
    """
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
async def reroll(task_id: str) -> dict:
    """Regenerate with the same prompt (reroll).

    Args:
        task_id: Task ID from imagine() or previous result
    """
    state = await tracker.get_task(task_id)
    if not state:
        return {"error": f"Task {task_id} not found"}

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
async def animate(task_id: str) -> dict:
    """Animate a generated image to create a short video.

    Args:
        task_id: Task ID from imagine() result
    """
    state = await tracker.get_task(task_id)
    if not state:
        return {"error": f"Task {task_id} not found"}

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


# ---- Tool: describe (note) -----------------------------------------------


@mcp.tool()
async def describe(image_url: str) -> dict:
    """Analyze an image and generate prompt suggestions.

    Args:
        image_url: Public URL of the image to describe
    """
    return {
        "note": "Midjourney /describe isn't supported via MCP yet (requires file upload to Discord). Use the Discord UI.",
    }


# ---- Callbacks: wire gateway events to tracker ---------------------------


async def _on_grid_complete(
    correlation_tag: str, task_id: str, image_url: str,
    message_id: str, upscale_buttons: dict, all_buttons: dict,
    has_animate: bool, **kwargs,
):
    await tracker.set_grid_complete(
        task_id, image_url, message_id,
        upscale_buttons, all_buttons, has_animate,
    )


async def _on_single_complete(
    correlation_tag: str, task_id: str, image_urls: list[str], message_id: str, **kwargs,
):
    """Handle a single image result — could be an upscale or a direct complete."""
    # Check if this task is in upscale phase
    state = await tracker.get_task(task_id)
    if state and state.status.value == "upscaling":
        # Try to derive which upscale index from the correlation context
        # The upscale index isn't passed in the callback, so we auto-assign
        # based on which slots are still empty
        url = image_urls[0] if image_urls else ""
        if url:
            for i in range(1, 5):
                if i not in state.upscale_results:
                    done = await tracker.record_upscale_result(task_id, i, url)
                    return
    await tracker.set_complete(task_id, image_urls)


async def _on_video_complete(
    correlation_tag: str, task_id: str, video_url: str, **kwargs,
):
    await tracker.set_video_complete(task_id, video_url)


async def _on_progress(correlation_tag: str, task_id: str, progress: int, **kwargs):
    await tracker.update_progress(task_id, progress)


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
            correlation_manager=correlation,
        )
        gateway.set_callbacks(
            on_progress=_on_progress,
            on_grid_complete=_on_grid_complete,
            on_single_complete=_on_single_complete,
            on_video_complete=_on_video_complete,
        )
        asyncio.create_task(gateway.start())
        logger.info("Gateway monitor started")
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
