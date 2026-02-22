"""ImagineService — orchestrates quota check, task creation, and dispatch enqueue."""

import asyncio
import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import QuotaExceededError
from app.models.api_key import ApiKey
from app.models.task import Task
from app.providers.discord.correlation import CorrelationManager
from app.services.quota_service import QuotaService
from app.services.task_service import TaskService

# Matches Midjourney parameter flags like --ar, --v, --style, etc.
_MJ_PARAM_PATTERN = re.compile(r"\s--\w+")
# Matches correlation tags that could spoof internal tracking
_CORRELATION_TAG_PATTERN = re.compile(r"mjr-[a-f0-9]+")


class ImagineService:
    def __init__(
        self,
        db: AsyncSession,
        dispatch_queue: asyncio.Queue[uuid.UUID],
        correlation: CorrelationManager,
    ) -> None:
        self._db = db
        self._task_svc = TaskService(db)
        self._quota_svc = QuotaService(db)
        self._dispatch_queue = dispatch_queue
        self._correlation = correlation

    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """Strip MJ parameter flags and reject correlation tag injection."""
        if _CORRELATION_TAG_PATTERN.search(prompt):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt must not contain reserved correlation tags (mjr-...)",
            )
        return _MJ_PARAM_PATTERN.sub("", prompt).strip()

    async def submit(
        self,
        api_key: ApiKey,
        prompt: str,
        aspect_ratio: str = "1:1",
    ) -> Task:
        # 0. Sanitize prompt
        prompt = self.sanitize_prompt(prompt)

        # 1. Check and deduct quota
        if not await self._quota_svc.check_and_deduct(api_key):
            raise QuotaExceededError()

        # 2. Create task
        task = await self._task_svc.create_task(
            api_key_id=api_key.id,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
        )

        # 3. Generate and set correlation tag
        tag = self._correlation.generate_tag()
        task = await self._task_svc.set_correlation_tag(task.id, tag)
        self._correlation.register(tag, str(task.id))

        # 4. Enqueue for dispatch
        await self._dispatch_queue.put(task.id)

        return task
