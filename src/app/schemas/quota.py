from pydantic import BaseModel


class QuotaResponse(BaseModel):
    daily_remaining: int
    daily_limit: int
    monthly_remaining: int
    monthly_limit: int
    platform_daily_remaining: int
