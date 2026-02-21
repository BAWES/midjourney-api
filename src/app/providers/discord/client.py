"""DiscordMidjourneyClient — combines InteractionClient and GatewayMonitor.

Implements the MidjourneyClient Protocol, owns discord.Client + httpx.AsyncClient,
and provides command metadata caching with TTL refresh on failure.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine

from app.providers.discord.correlation import CorrelationManager
from app.providers.discord.gateway import GatewayMonitor
from app.providers.discord.interaction import InteractionClient

logger = logging.getLogger(__name__)


class DiscordMidjourneyClient:
    def __init__(
        self,
        bot_token: str,
        user_token: str,
        channel_id: str,
    ) -> None:
        self._correlation = CorrelationManager()
        self._interaction = InteractionClient(
            user_token=user_token,
            channel_id=channel_id,
        )
        self._gateway = GatewayMonitor(
            bot_token=bot_token,
            channel_id=int(channel_id),
            correlation_manager=self._correlation,
        )
        self._bot_task: asyncio.Task | None = None

    @property
    def correlation_manager(self) -> CorrelationManager:
        return self._correlation

    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine],
        on_complete: Callable[..., Coroutine],
        on_error: Callable[..., Coroutine],
    ) -> None:
        self._gateway.set_callbacks(
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
        )

    async def start(self) -> None:
        await self._interaction.start()
        self._bot_task = asyncio.create_task(self._gateway.start())

    async def stop(self) -> None:
        await self._gateway.stop()
        await self._interaction.stop()
        if self._bot_task and not self._bot_task.done():
            self._bot_task.cancel()
            try:
                await self._bot_task
            except asyncio.CancelledError:
                pass

    async def imagine(
        self,
        prompt: str,
        aspect_ratio: str,
        correlation_tag: str,
    ) -> None:
        tagged_prompt = self._correlation.embed_in_prompt(prompt, correlation_tag)
        if aspect_ratio != "1:1":
            tagged_prompt = f"{tagged_prompt} --ar {aspect_ratio}"

        status_code = await self._interaction.send_imagine(tagged_prompt)
        if status_code == 204:
            logger.info("Interaction accepted for tag=%s", correlation_tag)
        else:
            # Force refresh command cache and retry once
            logger.warning(
                "Interaction failed (HTTP %d), retrying with refreshed command...",
                status_code,
            )
            self._interaction.invalidate_command_cache()
            status_code = await self._interaction.send_imagine(tagged_prompt)
            if status_code != 204:
                raise RuntimeError(
                    f"Failed to send /imagine after retry: HTTP {status_code}"
                )
