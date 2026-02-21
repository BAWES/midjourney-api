"""Tests for SQLAlchemy models — creation, constraints, defaults."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey, QuotaUsage
from app.models.base import TaskStatus
from app.models.task import Task, UsageLog


class TestApiKeyModel:
    async def test_create_api_key(self, db: AsyncSession) -> None:
        key = ApiKey(name="Test", key_hash="a" * 64, daily_limit=10, monthly_limit=100)
        db.add(key)
        await db.commit()
        await db.refresh(key)
        assert key.id is not None
        assert key.is_active is True
        assert key.created_at is not None

    async def test_api_key_hash_unique(self, db: AsyncSession) -> None:
        key1 = ApiKey(name="Key1", key_hash="unique_hash_1")
        key2 = ApiKey(name="Key2", key_hash="unique_hash_1")
        db.add(key1)
        await db.commit()
        db.add(key2)
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()

    async def test_api_key_defaults(self, db: AsyncSession) -> None:
        key = ApiKey(name="Defaults", key_hash="b" * 64)
        db.add(key)
        await db.commit()
        await db.refresh(key)
        assert key.daily_limit == 50
        assert key.monthly_limit == 1000
        assert key.is_active is True


class TestTaskModel:
    async def test_create_task(self, db: AsyncSession, api_key: ApiKey) -> None:
        task = Task(
            api_key_id=api_key.id,
            prompt="a cat",
            aspect_ratio="16:9",
            status=TaskStatus.QUEUED,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        assert task.id is not None
        assert task.progress == 0
        assert task.image_url is None

    async def test_task_status_enum(self, db: AsyncSession, api_key: ApiKey) -> None:
        task = Task(
            api_key_id=api_key.id, prompt="test", status=TaskStatus.PROCESSING
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        assert task.status == TaskStatus.PROCESSING


class TestQuotaUsageModel:
    async def test_create_quota_usage(self, db: AsyncSession, api_key: ApiKey) -> None:
        from datetime import date

        qu = QuotaUsage(
            api_key_id=api_key.id, usage_date=date.today(), daily_used=5
        )
        db.add(qu)
        await db.commit()
        await db.refresh(qu)
        assert qu.daily_used == 5

    async def test_unique_api_key_date(self, db: AsyncSession, api_key: ApiKey) -> None:
        from datetime import date

        today = date.today()
        qu1 = QuotaUsage(api_key_id=api_key.id, usage_date=today, daily_used=1)
        db.add(qu1)
        await db.commit()
        qu2 = QuotaUsage(api_key_id=api_key.id, usage_date=today, daily_used=2)
        db.add(qu2)
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()


class TestUsageLogModel:
    async def test_create_usage_log(self, db: AsyncSession, api_key: ApiKey) -> None:
        task = Task(
            api_key_id=api_key.id,
            prompt="test",
            status=TaskStatus.SUCCESS,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        log = UsageLog(
            task_id=task.id,
            api_key_id=api_key.id,
            prompt="test",
            aspect_ratio="1:1",
            status="success",
            duration_seconds=5.2,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        assert log.duration_seconds == 5.2
        assert log.task_id == task.id
