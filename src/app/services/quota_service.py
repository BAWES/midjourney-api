"""QuotaService — atomic quota check-and-deduct with rollback support."""

import uuid
from datetime import date, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.api_key import ApiKey, QuotaUsage


class QuotaService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def check_and_deduct(self, api_key: ApiKey) -> bool:
        today = date.today()

        # Check monthly limit
        first_of_month = today.replace(day=1)
        monthly_result = await self._db.execute(
            select(func.coalesce(func.sum(QuotaUsage.daily_used), 0)).where(
                QuotaUsage.api_key_id == api_key.id,
                QuotaUsage.usage_date >= first_of_month,
            )
        )
        monthly_used = monthly_result.scalar_one()
        if monthly_used >= api_key.monthly_limit:
            return False

        # Check platform-wide daily limit
        platform_result = await self._db.execute(
            select(func.coalesce(func.sum(QuotaUsage.daily_used), 0)).where(
                QuotaUsage.usage_date == today,
            )
        )
        platform_used = platform_result.scalar_one()
        if platform_used >= settings.platform_daily_limit:
            return False

        # Atomic daily check-and-deduct (row lock prevents TOCTOU race)
        existing = await self._db.execute(
            select(QuotaUsage)
            .where(
                QuotaUsage.api_key_id == api_key.id,
                QuotaUsage.usage_date == today,
            )
            .with_for_update()
        )
        quota = existing.scalar_one_or_none()

        if quota is None:
            quota = QuotaUsage(
                api_key_id=api_key.id,
                usage_date=today,
                daily_used=1,
            )
            self._db.add(quota)
            await self._db.commit()
            return True

        if quota.daily_used >= api_key.daily_limit:
            return False

        quota.daily_used += 1
        await self._db.commit()
        return True

    async def rollback(self, api_key: ApiKey) -> None:
        today = date.today()
        result = await self._db.execute(
            select(QuotaUsage).where(
                QuotaUsage.api_key_id == api_key.id,
                QuotaUsage.usage_date == today,
            )
        )
        quota = result.scalar_one_or_none()
        if quota and quota.daily_used > 0:
            quota.daily_used -= 1
            await self._db.commit()

    async def get_quota_info(self, api_key: ApiKey) -> dict:
        today = date.today()
        first_of_month = today.replace(day=1)

        # Daily usage
        daily_result = await self._db.execute(
            select(QuotaUsage).where(
                QuotaUsage.api_key_id == api_key.id,
                QuotaUsage.usage_date == today,
            )
        )
        daily_quota = daily_result.scalar_one_or_none()
        daily_used = daily_quota.daily_used if daily_quota else 0

        # Monthly usage
        monthly_result = await self._db.execute(
            select(func.coalesce(func.sum(QuotaUsage.daily_used), 0)).where(
                QuotaUsage.api_key_id == api_key.id,
                QuotaUsage.usage_date >= first_of_month,
            )
        )
        monthly_used = monthly_result.scalar_one()

        # Platform daily
        platform_result = await self._db.execute(
            select(func.coalesce(func.sum(QuotaUsage.daily_used), 0)).where(
                QuotaUsage.usage_date == today,
            )
        )
        platform_used = platform_result.scalar_one()

        return {
            "daily_remaining": max(0, api_key.daily_limit - daily_used),
            "daily_limit": api_key.daily_limit,
            "monthly_remaining": max(0, api_key.monthly_limit - monthly_used),
            "monthly_limit": api_key.monthly_limit,
            "platform_daily_remaining": max(0, settings.platform_daily_limit - platform_used),
        }
