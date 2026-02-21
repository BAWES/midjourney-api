"""Tests for ConcurrencyLimiter — dispatch queue, semaphore, timeout, callbacks."""

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.api_key import ApiKey
from app.models.base import TaskStatus
from app.providers.discord.correlation import CorrelationManager
from app.services.task_service import TaskService
from app.services.usage_service import UsageService
from app.core.concurrency import ConcurrencyLimiter


class TestConcurrencyLimiterDispatch:
    async def test_dispatch_transitions_to_processing(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test prompt", "1:1")
        task_id = task.id  # capture before expire
        correlation = CorrelationManager()
        tag = correlation.generate_tag()
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        mock_client.imagine = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.dispatch_one(task_id)

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.PROCESSING
        mock_client.imagine.assert_awaited_once()

    async def test_dispatch_calls_imagine_with_tagged_prompt(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "a beautiful cat", "16:9")
        task_id = task.id
        correlation = CorrelationManager()
        tag = correlation.generate_tag()
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.dispatch_one(task_id)

        call_args = mock_client.imagine.call_args
        assert tag in call_args.kwargs.get("prompt", call_args.args[0] if call_args.args else "")

    async def test_dispatch_failure_marks_failed(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1")
        task_id = task.id
        correlation = CorrelationManager()
        tag = correlation.generate_tag()
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        mock_client.imagine = AsyncMock(side_effect=RuntimeError("Discord error"))
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.dispatch_one(task_id)

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.FAILED


class TestConcurrencyLimiterCallbacks:
    async def test_on_complete_transitions_to_success(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1")
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        correlation = CorrelationManager()
        tag = "mjr-abcd1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.on_complete(tag, "https://cdn.example.com/image.png")

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.SUCCESS
        assert refreshed.image_url == "https://cdn.example.com/image.png"

    async def test_on_complete_creates_usage_log(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1")
        task_id = task.id
        api_key_id = api_key.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        correlation = CorrelationManager()
        tag = "mjr-abcd1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.on_complete(tag, "https://cdn.example.com/image.png")

        db.expire_all()
        usage_svc = UsageService(db)
        logs, total = await usage_svc.list_logs(api_key_id)
        assert total == 1
        assert logs[0].task_id == task_id

    async def test_on_error_marks_failed(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1")
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        correlation = CorrelationManager()
        tag = "mjr-abcd1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.on_error(tag, "Generation failed")

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.FAILED

    async def test_on_progress_updates_task(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1")
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        correlation = CorrelationManager()
        tag = "mjr-abcd1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.on_progress(tag, 50)

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.progress == 50


class TestConcurrencyLimiterTimeout:
    async def test_check_timeouts_marks_stale_tasks_failed(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1")
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)

        # Manually set updated_at to the past
        task.updated_at = datetime.utcnow() - timedelta(seconds=200)
        await db.commit()

        correlation = CorrelationManager()
        tag = "mjr-timeout1"
        correlation.register(tag, str(task_id))

        mock_client = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
            timeout_seconds=120,
        )
        await limiter.check_timeouts()

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.FAILED
