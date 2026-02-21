"""Tests for TaskService, QuotaService, and UsageService."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.base import TaskStatus
from app.models.task import Task
from app.exceptions import InvalidStateTransitionError, TaskNotFoundError
from app.services.task_service import TaskService
from app.services.quota_service import QuotaService
from app.services.usage_service import UsageService


# === TaskService Tests ===


class TestTaskService:
    async def test_create_task(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(
            api_key_id=api_key.id,
            prompt="a cat",
            aspect_ratio="1:1",
        )
        assert task.status == TaskStatus.QUEUED
        assert task.prompt == "a cat"
        assert task.progress == 0

    async def test_get_task_by_id(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(api_key_id=api_key.id, prompt="a dog")
        found = await svc.get_task(task.id, api_key_id=api_key.id)
        assert found is not None
        assert found.id == task.id

    async def test_get_task_wrong_api_key(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(api_key_id=api_key.id, prompt="a dog")
        with pytest.raises(TaskNotFoundError):
            await svc.get_task(task.id, api_key_id=uuid.uuid4())

    async def test_get_task_not_found(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        with pytest.raises(TaskNotFoundError):
            await svc.get_task(uuid.uuid4(), api_key_id=api_key.id)

    async def test_list_tasks_paginated(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        for i in range(5):
            await svc.create_task(api_key_id=api_key.id, prompt=f"prompt {i}")
        items, total = await svc.list_tasks(api_key_id=api_key.id, page=1, page_size=3)
        assert len(items) == 3
        assert total == 5

    async def test_transition_queued_to_processing(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(api_key_id=api_key.id, prompt="test")
        updated = await svc.transition(task.id, TaskStatus.PROCESSING)
        assert updated.status == TaskStatus.PROCESSING

    async def test_transition_processing_to_success(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(api_key_id=api_key.id, prompt="test")
        await svc.transition(task.id, TaskStatus.PROCESSING)
        updated = await svc.transition(task.id, TaskStatus.SUCCESS)
        assert updated.status == TaskStatus.SUCCESS

    async def test_transition_processing_to_failed(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(api_key_id=api_key.id, prompt="test")
        await svc.transition(task.id, TaskStatus.PROCESSING)
        updated = await svc.transition(task.id, TaskStatus.FAILED)
        assert updated.status == TaskStatus.FAILED

    async def test_reject_invalid_transition(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(api_key_id=api_key.id, prompt="test")
        await svc.transition(task.id, TaskStatus.PROCESSING)
        await svc.transition(task.id, TaskStatus.SUCCESS)
        with pytest.raises(InvalidStateTransitionError):
            await svc.transition(task.id, TaskStatus.QUEUED)

    async def test_update_progress(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = TaskService(db)
        task = await svc.create_task(api_key_id=api_key.id, prompt="test")
        await svc.transition(task.id, TaskStatus.PROCESSING)
        updated = await svc.update_progress(task.id, 50)
        assert updated.progress == 50


# === QuotaService Tests ===


class TestQuotaService:
    async def test_check_and_deduct_daily(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = QuotaService(db)
        result = await svc.check_and_deduct(api_key)
        assert result is True

    async def test_daily_limit_enforced(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = QuotaService(db)
        # Set daily limit to 2
        api_key.daily_limit = 2
        await db.commit()
        assert await svc.check_and_deduct(api_key) is True
        assert await svc.check_and_deduct(api_key) is True
        assert await svc.check_and_deduct(api_key) is False

    async def test_get_quota_info(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = QuotaService(db)
        await svc.check_and_deduct(api_key)
        info = await svc.get_quota_info(api_key)
        assert info["daily_remaining"] == api_key.daily_limit - 1
        assert info["daily_limit"] == api_key.daily_limit

    async def test_rollback(self, db: AsyncSession, api_key: ApiKey) -> None:
        svc = QuotaService(db)
        await svc.check_and_deduct(api_key)
        await svc.rollback(api_key)
        info = await svc.get_quota_info(api_key)
        assert info["daily_remaining"] == api_key.daily_limit


# === UsageService Tests ===


class TestUsageService:
    async def test_create_usage_log(self, db: AsyncSession, api_key: ApiKey) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key_id=api_key.id, prompt="test")
        await task_svc.transition(task.id, TaskStatus.PROCESSING)
        await task_svc.transition(task.id, TaskStatus.SUCCESS)

        usage_svc = UsageService(db)
        log = await usage_svc.create_log(
            task=task,
            api_key_id=api_key.id,
        )
        assert log.task_id == task.id
        assert log.status == "success"
        assert log.duration_seconds is not None
        assert log.duration_seconds >= 0

    async def test_list_usage_paginated(self, db: AsyncSession, api_key: ApiKey) -> None:
        task_svc = TaskService(db)
        usage_svc = UsageService(db)

        for i in range(3):
            task = await task_svc.create_task(api_key_id=api_key.id, prompt=f"p{i}")
            await task_svc.transition(task.id, TaskStatus.PROCESSING)
            await task_svc.transition(task.id, TaskStatus.SUCCESS)
            await usage_svc.create_log(task=task, api_key_id=api_key.id)

        items, total = await usage_svc.list_logs(
            api_key_id=api_key.id, page=1, page_size=2
        )
        assert len(items) == 2
        assert total == 3
