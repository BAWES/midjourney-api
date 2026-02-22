"""TaskService — task lifecycle management with state machine validation."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidStateTransitionError, TaskNotFoundError
from app.models.base import TaskStatus
from app.models.task import Task

VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.PROCESSING, TaskStatus.FAILED},
    TaskStatus.PROCESSING: {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.UPSCALING},
    TaskStatus.UPSCALING: {TaskStatus.SUCCESS, TaskStatus.FAILED},
    TaskStatus.SUCCESS: set(),
    TaskStatus.FAILED: set(),
}


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_task(
        self,
        api_key_id: uuid.UUID,
        prompt: str,
        aspect_ratio: str = "1:1",
        upscale_count: int = 1,
    ) -> Task:
        task = Task(
            api_key_id=api_key_id,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            status=TaskStatus.QUEUED,
            progress=0,
            upscale_count=upscale_count,
        )
        self._db.add(task)
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def get_task(
        self,
        task_id: uuid.UUID,
        api_key_id: uuid.UUID,
    ) -> Task:
        result = await self._db.execute(
            select(Task).where(Task.id == task_id, Task.api_key_id == api_key_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return task

    async def get_task_by_id(self, task_id: uuid.UUID) -> Task:
        result = await self._db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return task

    async def list_tasks(
        self,
        api_key_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        count_result = await self._db.execute(
            select(func.count()).select_from(Task).where(Task.api_key_id == api_key_id)
        )
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self._db.execute(
            select(Task)
            .where(Task.api_key_id == api_key_id)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total

    async def transition(
        self,
        task_id: uuid.UUID,
        target_status: TaskStatus,
    ) -> Task:
        task = await self.get_task_by_id(task_id)
        if target_status not in VALID_TRANSITIONS.get(task.status, set()):
            raise InvalidStateTransitionError(task.status.value, target_status.value)
        task.status = target_status
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def update_progress(self, task_id: uuid.UUID, progress: int) -> Task:
        task = await self.get_task_by_id(task_id)
        task.progress = progress
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def update_image_url(self, task_id: uuid.UUID, image_url: str) -> Task:
        task = await self.get_task_by_id(task_id)
        task.image_url = image_url
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def update_image_urls(
        self, task_id: uuid.UUID, image_urls: list[str]
    ) -> Task:
        task = await self.get_task_by_id(task_id)
        task.image_urls = image_urls
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def set_correlation_tag(self, task_id: uuid.UUID, tag: str) -> Task:
        task = await self.get_task_by_id(task_id)
        task.correlation_tag = tag
        await self._db.commit()
        await self._db.refresh(task)
        return task
