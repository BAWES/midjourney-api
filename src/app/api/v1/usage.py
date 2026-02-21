"""Usage API endpoint — list usage logs with pagination and date filtering."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session
from app.models.api_key import ApiKey
from app.schemas.usage import UsageListResponse, UsageLogResponse
from app.services.usage_service import UsageService

router = APIRouter(tags=["usage"])


@router.get("/usage", response_model=UsageListResponse)
async def list_usage(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> UsageListResponse:
    svc = UsageService(db)
    items, total = await svc.list_logs(
        api_key_id=api_key.id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )
    return UsageListResponse(
        items=[UsageLogResponse.model_validate(log) for log in items],
        total=total,
        page=page,
        page_size=page_size,
    )
