"""Task API endpoints — get task, list tasks."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session
from app.models.api_key import ApiKey
from app.schemas.task import TaskListResponse, TaskResponse
from app.services.task_service import TaskService

router = APIRouter(tags=["tasks"])


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    svc = TaskService(db)
    task = await svc.get_task(task_id, api_key_id=api_key.id)
    return TaskResponse.model_validate(task)


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> TaskListResponse:
    svc = TaskService(db)
    items, total = await svc.list_tasks(api_key.id, page=page, page_size=page_size)
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )
