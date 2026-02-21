"""V1 API aggregated router."""

from fastapi import APIRouter

from app.api.v1 import imagine, quota, tasks, usage

router = APIRouter()
router.include_router(imagine.router)
router.include_router(tasks.router)
router.include_router(quota.router)
router.include_router(usage.router)
