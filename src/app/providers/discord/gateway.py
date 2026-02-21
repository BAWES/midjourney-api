"""Discord Gateway monitor for Midjourney Bot messages.

Connects via discord.py, filters by channel and MJ Bot ID,
parses messages, and invokes callbacks.
"""

import logging
from collections.abc import Callable, Coroutine

import discord

from app.providers.discord.parser import extract_progress, is_completed, extract_image_url
from app.providers.discord.correlation import CorrelationManager

logger = logging.getLogger(__name__)

MJ_BOT_ID = 936929561302675456


class GatewayMonitor:
    def __init__(
        self,
        bot_token: str,
        channel_id: int,
        correlation_manager: CorrelationManager,
    ) -> None:
        self._bot_token = bot_token
        self._channel_id = channel_id
        self._correlation = correlation_manager
        self._on_progress: Callable[..., Coroutine] | None = None
        self._on_complete: Callable[..., Coroutine] | None = None
        self._on_error: Callable[..., Coroutine] | None = None

        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        self._client.event(self._on_message)
        self._client.event(self._on_message_edit)

    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine],
        on_complete: Callable[..., Coroutine],
        on_error: Callable[..., Coroutine],
    ) -> None:
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error

    async def start(self) -> None:
        await self._client.start(self._bot_token)

    async def stop(self) -> None:
        await self._client.close()

    def _should_process(self, message: discord.Message) -> bool:
        return (
            message.channel.id == self._channel_id
            and message.author.id == MJ_BOT_ID
        )

    async def _handle_message(self, message: discord.Message) -> None:
        if not self._should_process(message):
            return

        tag = self._correlation.extract_tag(message.content)
        if not tag:
            return

        task_id = self._correlation.lookup(tag)
        if not task_id:
            logger.warning("Unknown correlation tag: %s", tag)
            return

        if is_completed(message):
            image_url = extract_image_url(message)
            if self._on_complete:
                await self._on_complete(
                    correlation_tag=tag,
                    task_id=task_id,
                    image_url=image_url,
                )
        else:
            progress = extract_progress(message.content)
            if progress is not None and self._on_progress:
                await self._on_progress(
                    correlation_tag=tag,
                    task_id=task_id,
                    progress=progress,
                )

    async def _on_message(self, message: discord.Message) -> None:
        await self._handle_message(message)

    # Rename for discord.py event registration
    _on_message.__name__ = "on_message"

    async def _on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        await self._handle_message(after)

    _on_message_edit.__name__ = "on_message_edit"
