"""ConcurrencyLimiter — semaphore-based dispatch queue with timeout checker."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.upscale_tracker import UpscaleTracker
from app.models.api_key import ApiKey
from app.models.base import TaskStatus
from app.models.task import Task
from app.providers.discord.correlation import CorrelationManager
from app.providers.protocol import MidjourneyClient
from app.services.quota_service import QuotaService
from app.services.task_service import TaskService
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)


class ConcurrencyLimiter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mj_client: MidjourneyClient,
        correlation: CorrelationManager,
        dispatch_queue: asyncio.Queue[uuid.UUID],
        max_concurrent: int = 3,
        timeout_seconds: int = 120,
        upscale_timeout_seconds: int = 180,
    ) -> None:
        self._session_factory = session_factory
        self._mj_client = mj_client
        self._correlation = correlation
        self._queue = dispatch_queue
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = timeout_seconds
        self._upscale_timeout = upscale_timeout_seconds
        self._running = False
        self._bg_tasks: set[asyncio.Task] = set()
        self._consumer_task: asyncio.Task | None = None
        self._timeout_task: asyncio.Task | None = None
        self._upscale_tracker = UpscaleTracker()

    async def start(self) -> None:
        self._running = True
        self._mj_client.set_callbacks(
            on_progress=self.on_progress,
            on_complete=self.on_complete,
            on_error=self.on_error,
            on_grid_complete=self.on_grid_complete,
            on_upscale_result=self.on_upscale_result,
        )
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        self._timeout_task = asyncio.create_task(self._timeout_loop())

    async def stop(self) -> None:
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
        if self._timeout_task:
            self._timeout_task.cancel()
        for t in self._bg_tasks:
            t.cancel()

    async def _consumer_loop(self) -> None:
        while self._running:
            task_id = await self._queue.get()
            await self._semaphore.acquire()
            t = asyncio.create_task(self._dispatch_wrapper(task_id))
            self._bg_tasks.add(t)
            t.add_done_callback(self._bg_tasks.discard)

    async def _dispatch_wrapper(self, task_id: uuid.UUID) -> None:
        try:
            await self.dispatch_one(task_id)
        except Exception:
            logger.exception("Dispatch failed for task %s", task_id)
            self._semaphore.release()

    async def dispatch_one(self, task_id: uuid.UUID) -> None:
        async with self._session_factory() as db:
            task_svc = TaskService(db)
            try:
                task = await task_svc.get_task_by_id(task_id)
                await task_svc.transition(task_id, TaskStatus.PROCESSING)

                self._mj_client.set_upscale_count(
                    task.correlation_tag, task.upscale_count
                )
                await self._mj_client.imagine(
                    prompt=task.prompt,
                    aspect_ratio=task.aspect_ratio,
                    correlation_tag=task.correlation_tag,
                )
            except Exception:
                logger.exception("Dispatch error for task %s", task_id)
                try:
                    await task_svc.transition(task_id, TaskStatus.FAILED)
                except Exception:
                    logger.exception(
                        "Failed to transition task %s to FAILED", task_id
                    )
                raise

    async def on_progress(self, correlation_tag: str, progress: int, **kwargs: object) -> None:
        tag = correlation_tag
        task_id_str = self._correlation.lookup(tag)
        if not task_id_str:
            return
        # Fast path: if tracker has this task, it's in UPSCALING phase — skip DB query
        if self._upscale_tracker.get(task_id_str) is not None:
            return
        async with self._session_factory() as db:
            task_svc = TaskService(db)
            task = await task_svc.get_task_by_id(uuid.UUID(task_id_str))
            if task.status == TaskStatus.UPSCALING:
                return
            await task_svc.update_progress(task.id, progress)

    async def on_complete(self, correlation_tag: str, image_url: str, **kwargs: object) -> None:
        """Handle direct completion (no upscale buttons — legacy path)."""
        tag = correlation_tag
        task_id_str = self._correlation.lookup(tag)
        if not task_id_str:
            return
        task_id = uuid.UUID(task_id_str)
        async with self._session_factory() as db:
            task_svc = TaskService(db)
            usage_svc = UsageService(db)
            await task_svc.update_image_url(task_id, image_url)
            task = await task_svc.transition(task_id, TaskStatus.SUCCESS)
            await usage_svc.create_log(task=task, api_key_id=task.api_key_id)
        self._correlation.unregister(tag)
        self._semaphore.release()

    async def on_grid_complete(
        self,
        correlation_tag: str,
        image_url: str,
        message_id: str,
        upscale_buttons: dict[int, str],
        **kwargs: object,
    ) -> None:
        """Handle grid completion: save grid URL, transition to UPSCALING, send upscale interactions."""
        tag = correlation_tag
        task_id_str = self._correlation.lookup(tag)
        if not task_id_str:
            return
        task_id = uuid.UUID(task_id_str)

        async with self._session_factory() as db:
            task_svc = TaskService(db)
            await task_svc.update_image_url(task_id, image_url)
            task = await task_svc.get_task_by_id(task_id)
            upscale_count = task.upscale_count
            await task_svc.transition(task_id, TaskStatus.UPSCALING)

        # Register tracker before sending interactions (avoid race condition)
        buttons_to_use = {i: upscale_buttons[i] for i in range(1, upscale_count + 1) if i in upscale_buttons}
        self._upscale_tracker.start(
            task_id=task_id_str,
            upscale_count=upscale_count,
            grid_image_url=image_url,
            message_id=message_id,
            button_custom_ids=buttons_to_use,
        )

        # Send upscale interactions for U1..U(upscale_count)
        for i in range(1, upscale_count + 1):
            custom_id = upscale_buttons.get(i)
            if custom_id:
                try:
                    await self._mj_client.upscale(message_id, custom_id)
                except Exception:
                    logger.exception("Failed to send upscale U%d for task %s", i, task_id_str)
                    self._upscale_tracker.record_error(task_id_str, i, f"Failed to send U{i}")
            else:
                logger.warning("Missing upscale button U%d for task %s", i, task_id_str)
                self._upscale_tracker.record_error(task_id_str, i, f"Button U{i} not found")

        # Check if all upscales already failed during send
        state = self._upscale_tracker.get(task_id_str)
        if state and state.is_complete:
            await self._finalize_upscale(tag, task_id_str)

    async def on_upscale_result(
        self,
        correlation_tag: str,
        image_url: str,
        upscale_index: int,
        **kwargs: object,
    ) -> None:
        """Handle individual upscale result."""
        tag = correlation_tag
        task_id_str = self._correlation.lookup(tag)
        if not task_id_str:
            return

        state = self._upscale_tracker.record_result(task_id_str, upscale_index, image_url)
        if state is None:
            logger.warning("Upscale result for unknown task %s (already finalized?)", task_id_str)
            return

        # Update progress based on completed count
        progress = int(state.completed_count / state.upscale_count * 100)
        async with self._session_factory() as db:
            task_svc = TaskService(db)
            await task_svc.update_progress(uuid.UUID(task_id_str), progress)

        if state.is_complete:
            await self._finalize_upscale(tag, task_id_str)

    async def _finalize_upscale(self, tag: str, task_id_str: str) -> None:
        """Complete the upscale phase: save URLs, transition, release semaphore.

        Uses atomic pop() to prevent double finalization from concurrent paths.
        """
        # Atomic pop — only one caller gets the state
        state = self._upscale_tracker.pop(task_id_str)
        if state is None:
            return

        task_id = uuid.UUID(task_id_str)
        image_urls = state.get_image_urls()

        async with self._session_factory() as db:
            task_svc = TaskService(db)
            usage_svc = UsageService(db)

            if image_urls:
                await task_svc.update_image_urls(task_id, image_urls)

            if state.success_count > 0:
                task = await task_svc.transition(task_id, TaskStatus.SUCCESS)
            else:
                task = await task_svc.get_task_by_id(task_id)
                task.error_message = "All upscale requests failed"
                await db.commit()
                task = await task_svc.transition(task_id, TaskStatus.FAILED)

            await usage_svc.create_log(task=task, api_key_id=task.api_key_id)

        self._correlation.unregister(tag)
        self._semaphore.release()

    async def on_error(self, correlation_tag: str, error_message: str, **kwargs: object) -> None:
        tag = correlation_tag
        task_id_str = self._correlation.lookup(tag)
        if not task_id_str:
            return
        task_id = uuid.UUID(task_id_str)
        # Clean up any in-flight upscale state to prevent late callbacks
        self._upscale_tracker.remove(task_id_str)
        async with self._session_factory() as db:
            task_svc = TaskService(db)
            task = await task_svc.get_task_by_id(task_id)
            task.error_message = error_message
            await db.commit()
            await task_svc.transition(task_id, TaskStatus.FAILED)
            # Rollback quota
            result = await db.execute(
                select(ApiKey).where(ApiKey.id == task.api_key_id)
            )
            api_key = result.scalar_one_or_none()
            if api_key:
                quota_svc = QuotaService(db)
                await quota_svc.rollback(api_key)
        self._correlation.unregister(tag)
        self._semaphore.release()

    async def _timeout_loop(self) -> None:
        while self._running:
            await asyncio.sleep(10)
            await self.check_timeouts()

    async def check_timeouts(self) -> None:
        now = datetime.now(timezone.utc)

        async with self._session_factory() as db:
            task_svc = TaskService(db)

            # Query 1: PROCESSING tasks with standard timeout
            processing_cutoff = now - timedelta(seconds=self._timeout)
            result = await db.execute(
                select(Task).where(
                    Task.status == TaskStatus.PROCESSING,
                    Task.updated_at < processing_cutoff,
                )
            )
            for task in result.scalars().all():
                try:
                    task.error_message = f"Task timed out after {self._timeout}s"
                    await db.commit()
                    await task_svc.transition(task.id, TaskStatus.FAILED)
                    if task.correlation_tag:
                        self._correlation.unregister(task.correlation_tag)
                    self._semaphore.release()
                except Exception:
                    logger.exception("Failed to timeout PROCESSING task %s", task.id)

            # Query 2: UPSCALING tasks with upscale timeout
            upscale_cutoff = now - timedelta(seconds=self._upscale_timeout)
            result = await db.execute(
                select(Task).where(
                    Task.status == TaskStatus.UPSCALING,
                    Task.updated_at < upscale_cutoff,
                )
            )
            for task in result.scalars().all():
                try:
                    task_id_str = str(task.id)
                    # Atomic pop to prevent race with on_upscale_result
                    state = self._upscale_tracker.pop(task_id_str)
                    if state is None:
                        # Already finalized by another path — skip
                        continue
                    if state.get_image_urls():
                        task.image_urls = state.get_image_urls()

                    task.error_message = f"Upscale timed out after {self._upscale_timeout}s"
                    await db.commit()
                    await task_svc.transition(task.id, TaskStatus.FAILED)
                    if task.correlation_tag:
                        self._correlation.unregister(task.correlation_tag)
                    self._semaphore.release()
                except Exception:
                    logger.exception("Failed to timeout UPSCALING task %s", task.id)

    async def recover(self) -> None:
        """Rebuild semaphore and correlation map from active tasks."""
        async with self._session_factory() as db:
            task_svc = TaskService(db)

            # Recover PROCESSING tasks (can resume monitoring)
            result = await db.execute(
                select(Task).where(Task.status == TaskStatus.PROCESSING)
            )
            active_tasks = list(result.scalars().all())
            for task in active_tasks:
                await self._semaphore.acquire()
                if task.correlation_tag:
                    self._correlation.register(task.correlation_tag, str(task.id))

            # UPSCALING tasks cannot be recovered (in-memory state lost).
            # No semaphore acquire/release needed: semaphore is fresh on restart,
            # and we only acquire for PROCESSING tasks that remain active.
            # UPSCALING tasks are failed immediately, freeing their slots implicitly.
            result = await db.execute(
                select(Task).where(Task.status == TaskStatus.UPSCALING)
            )
            upscaling_tasks = list(result.scalars().all())
            for task in upscaling_tasks:
                logger.warning(
                    "UPSCALING task %s cannot be recovered, marking FAILED", task.id
                )
                task.error_message = "Upscale state lost due to server restart"
                await db.commit()
                await task_svc.transition(task.id, TaskStatus.FAILED)
                if task.correlation_tag:
                    self._correlation.unregister(task.correlation_tag)
