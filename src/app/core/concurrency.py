"""ConcurrencyLimiter — semaphore-based dispatch queue with timeout checker."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.api_key import ApiKey
from app.models.base import TaskStatus
from app.models.task import Task
from app.providers.discord.correlation import CorrelationManager
from app.services.quota_service import QuotaService
from app.services.task_service import TaskService
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)


class ConcurrencyLimiter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mj_client: object,
        correlation: CorrelationManager,
        dispatch_queue: asyncio.Queue[uuid.UUID],
        max_concurrent: int = 3,
        timeout_seconds: int = 120,
    ) -> None:
        self._session_factory = session_factory
        self._mj_client = mj_client
        self._correlation = correlation
        self._queue = dispatch_queue
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = timeout_seconds
        self._running = False
        self._bg_tasks: set[asyncio.Task] = set()
        self._consumer_task: asyncio.Task | None = None
        self._timeout_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._mj_client.set_callbacks(
            on_progress=self.on_progress,
            on_complete=self.on_complete,
            on_error=self.on_error,
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
                    pass
                self._semaphore.release()

    async def on_progress(self, correlation_tag: str, progress: int, **kwargs: object) -> None:
        tag = correlation_tag
        task_id_str = self._correlation.lookup(tag)
        if not task_id_str:
            return
        async with self._session_factory() as db:
            task_svc = TaskService(db)
            await task_svc.update_progress(uuid.UUID(task_id_str), progress)

    async def on_complete(self, correlation_tag: str, image_url: str, **kwargs: object) -> None:
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

    async def on_error(self, correlation_tag: str, error_message: str, **kwargs: object) -> None:
        tag = correlation_tag
        task_id_str = self._correlation.lookup(tag)
        if not task_id_str:
            return
        task_id = uuid.UUID(task_id_str)
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
        cutoff = datetime.utcnow() - timedelta(seconds=self._timeout)
        async with self._session_factory() as db:
            result = await db.execute(
                select(Task).where(
                    Task.status == TaskStatus.PROCESSING,
                    Task.updated_at < cutoff,
                )
            )
            timed_out = list(result.scalars().all())
            task_svc = TaskService(db)
            for task in timed_out:
                task.error_message = f"Task timed out after {self._timeout}s"
                await db.commit()
                await task_svc.transition(task.id, TaskStatus.FAILED)
                if task.correlation_tag:
                    self._correlation.unregister(task.correlation_tag)
                self._semaphore.release()

    async def recover(self) -> None:
        """Rebuild semaphore and correlation map from active PROCESSING tasks."""
        async with self._session_factory() as db:
            result = await db.execute(
                select(Task).where(Task.status == TaskStatus.PROCESSING)
            )
            active_tasks = list(result.scalars().all())
            for task in active_tasks:
                await self._semaphore.acquire()
                if task.correlation_tag:
                    self._correlation.register(task.correlation_tag, str(task.id))
