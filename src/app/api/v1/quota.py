"""Quota API endpoint — get remaining quota info."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session
from app.models.api_key import ApiKey
from app.schemas.quota import QuotaResponse
from app.services.quota_service import QuotaService

router = APIRouter(tags=["quota"])


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> QuotaResponse:
    svc = QuotaService(db)
    info = await svc.get_quota_info(api_key)
    return QuotaResponse(**info)
