"""Discord Gateway monitor for Midjourney Bot messages.

Connects via discord.py, filters by channel and MJ Bot ID,
parses messages, and fires callbacks for the MCP task tracker.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine

import discord

from mj_mcp.discord.correlation import CorrelationManager
from mj_mcp.discord.parser import (
    extract_all_image_urls,
    extract_all_buttons,
    extract_image_url,
    extract_progress,
    extract_upscale_buttons,
    has_animate_button,
    is_completed,
    is_grid_completion,
    is_video_result,
)

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

        # Callback hooks — set by task tracker
        self._on_progress: Callable[..., Coroutine] | None = None
        self._on_grid_complete: Callable[..., Coroutine] | None = None
        self._on_single_complete: Callable[..., Coroutine] | None = None
        self._on_video_complete: Callable[..., Coroutine] | None = None

        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        self._client.event(self._on_message)
        self._client.event(self._on_message_edit)
        self._client.event(self._on_ready)

    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine] | None = None,
        on_grid_complete: Callable[..., Coroutine] | None = None,
        on_single_complete: Callable[..., Coroutine] | None = None,
        on_video_complete: Callable[..., Coroutine] | None = None,
    ) -> None:
        self._on_progress = on_progress
        self._on_grid_complete = on_grid_complete
        self._on_single_complete = on_single_complete
        self._on_video_complete = on_video_complete

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
            logger.debug("Skipping message from %s in channel %s (not MJ bot or wrong channel)",
                         message.author.id, message.channel.id)
            return

        tag = self._correlation.extract_tag(message.content)
        logger.info("MJ message from bot: tag=%s content=%.80s attachments=%d",
                     tag, message.content, len(message.attachments) if message.attachments else 0)
        if not tag:
            return
        task_id = self._correlation.lookup(tag)
        if not task_id:
            logger.warning("Unknown correlation tag: %s", tag)
            return

        # 1. Video result?
        if is_video_result(message) and self._on_video_complete:
            await self._on_video_complete(
                correlation_tag=tag,
                task_id=task_id,
                video_url=extract_image_url(message),
            )
            return

        # 2. Grid completion (has U1-U4 buttons)
        if is_grid_completion(message) and self._on_grid_complete:
            image_url = extract_image_url(message)
            buttons = extract_upscale_buttons(message)
            all_buttons = extract_all_buttons(message)
            await self._on_grid_complete(
                correlation_tag=tag,
                task_id=task_id,
                image_url=image_url,
                message_id=str(message.id),
                upscale_buttons=buttons,
                all_buttons=all_buttons,
                has_animate=has_animate_button(message),
            )
            return

        # 3. Single image completion (upscale, variation result, direct complete)
        if is_completed(message) and self._on_single_complete:
            urls = extract_all_image_urls(message)
            await self._on_single_complete(
                correlation_tag=tag,
                task_id=task_id,
                image_urls=urls,
                message_id=str(message.id),
            )
            return

        # 4. Progress update
        progress = extract_progress(message.content)
        if progress is not None and self._on_progress:
            await self._on_progress(
                correlation_tag=tag,
                task_id=task_id,
                progress=progress,
            )

    async def _on_message(self, message: discord.Message) -> None:
        await self._handle_message(message)

    _on_message.__name__ = "on_message"

    async def _on_message_edit(
        self, before: discord.Message, after: discord.Message
    ) -> None:
        await self._handle_message(after)

    _on_message_edit.__name__ = "on_message_edit"

    async def _on_ready(self) -> None:
        """Called when discord.py connects successfully."""
        logger.info(
            "Gateway connected! Bot: %s (ID: %s)",
            self._client.user.name if self._client.user else "?",
            self._client.user.id if self._client.user else "?",
        )

    _on_ready.__name__ = "on_ready"
