"""UsageService — create usage logs on task completion."""

import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, UsageLog


class UsageService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_log(
        self,
        task: Task,
        api_key_id: uuid.UUID,
    ) -> UsageLog:
        duration = None
        if task.created_at and task.updated_at:
            duration = (task.updated_at - task.created_at).total_seconds()

        log = UsageLog(
            task_id=task.id,
            api_key_id=api_key_id,
            prompt=task.prompt,
            aspect_ratio=task.aspect_ratio,
            status=task.status.value,
            image_url=task.image_url,
            duration_seconds=duration,
        )
        self._db.add(log)
        await self._db.commit()
        await self._db.refresh(log)
        return log

    async def list_logs(
        self,
        api_key_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[UsageLog], int]:
        query = select(UsageLog).where(UsageLog.api_key_id == api_key_id)
        count_query = select(func.count()).select_from(UsageLog).where(
            UsageLog.api_key_id == api_key_id
        )

        if start_date:
            query = query.where(UsageLog.created_at >= datetime.combine(start_date, datetime.min.time()))
            count_query = count_query.where(UsageLog.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.where(UsageLog.created_at <= datetime.combine(end_date, datetime.max.time()))
            count_query = count_query.where(UsageLog.created_at <= datetime.combine(end_date, datetime.max.time()))

        total_result = await self._db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self._db.execute(
            query.order_by(UsageLog.created_at.desc()).offset(offset).limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total
