import uuid
from datetime import datetime

from pydantic import BaseModel


class UsageLogResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    prompt: str
    aspect_ratio: str
    status: str
    image_url: str | None = None
    duration_seconds: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageListResponse(BaseModel):
    items: list[UsageLogResponse]
    total: int
    page: int
    page_size: int
