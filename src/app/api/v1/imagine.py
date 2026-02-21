"""Imagine API endpoint — submit image generation request."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session
from app.models.api_key import ApiKey
from app.schemas.task import ImagineRequest, ImagineResponse
from app.services.imagine_service import ImagineService

router = APIRouter(tags=["imagine"])

# These will be injected at app startup via set_dependencies()
_dispatch_queue = None
_correlation = None


def set_dependencies(dispatch_queue, correlation) -> None:
    global _dispatch_queue, _correlation
    _dispatch_queue = dispatch_queue
    _correlation = correlation


@router.post("/imagine", response_model=ImagineResponse, status_code=status.HTTP_202_ACCEPTED)
async def imagine(
    body: ImagineRequest,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> ImagineResponse:
    svc = ImagineService(db, _dispatch_queue, _correlation)
    task = await svc.submit(api_key, body.prompt, body.aspect_ratio)
    return ImagineResponse(task_id=task.id, status=task.status.value)
