"""Tests for ImagineService orchestrator."""

import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import QuotaExceededError
from app.models.api_key import ApiKey
from app.models.base import TaskStatus
from app.providers.discord.correlation import CorrelationManager
from app.services.imagine_service import ImagineService


class TestImagineService:
    async def test_submit_creates_queued_task(
        self, db: AsyncSession, api_key: ApiKey
    ) -> None:
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        correlation = CorrelationManager()
        svc = ImagineService(db, queue, correlation)
        task = await svc.submit(api_key, "a cat", "16:9")
        assert task.status == TaskStatus.QUEUED
        assert task.prompt == "a cat"
        assert task.aspect_ratio == "16:9"

    async def test_submit_deducts_quota(
        self, db: AsyncSession, api_key: ApiKey
    ) -> None:
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        correlation = CorrelationManager()
        svc = ImagineService(db, queue, correlation)
        await svc.submit(api_key, "a cat")

        from app.services.quota_service import QuotaService

        info = await QuotaService(db).get_quota_info(api_key)
        assert info["daily_remaining"] == api_key.daily_limit - 1

    async def test_submit_quota_exceeded(
        self, db: AsyncSession, api_key: ApiKey
    ) -> None:
        api_key.daily_limit = 1
        await db.commit()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        correlation = CorrelationManager()
        svc = ImagineService(db, queue, correlation)
        await svc.submit(api_key, "first")
        with pytest.raises(QuotaExceededError):
            await svc.submit(api_key, "second")

    async def test_submit_sets_correlation_tag(
        self, db: AsyncSession, api_key: ApiKey
    ) -> None:
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        correlation = CorrelationManager()
        svc = ImagineService(db, queue, correlation)
        task = await svc.submit(api_key, "a cat")
        assert task.correlation_tag is not None
        assert task.correlation_tag.startswith("mjr-")

    async def test_submit_registers_correlation(
        self, db: AsyncSession, api_key: ApiKey
    ) -> None:
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        correlation = CorrelationManager()
        svc = ImagineService(db, queue, correlation)
        task = await svc.submit(api_key, "a cat")
        looked_up = correlation.lookup(task.correlation_tag)
        assert looked_up == str(task.id)

    async def test_submit_enqueues_task_id(
        self, db: AsyncSession, api_key: ApiKey
    ) -> None:
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        correlation = CorrelationManager()
        svc = ImagineService(db, queue, correlation)
        task = await svc.submit(api_key, "a cat")
        assert not queue.empty()
        enqueued_id = await queue.get()
        assert enqueued_id == task.id

    async def test_submit_rollbacks_quota_on_failure(
        self, db: AsyncSession, api_key: ApiKey
    ) -> None:
        """If task creation fails after quota deduction, quota should be rolled back."""
        api_key.daily_limit = 1
        await db.commit()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        correlation = CorrelationManager()
        svc = ImagineService(db, queue, correlation)
        await svc.submit(api_key, "first")

        from app.services.quota_service import QuotaService

        info = await QuotaService(db).get_quota_info(api_key)
        assert info["daily_remaining"] == 0
