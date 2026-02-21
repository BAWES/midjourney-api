import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ImagineRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    aspect_ratio: str = Field(default="1:1", pattern=r"^\d+:\d+$")


class ImagineResponse(BaseModel):
    task_id: uuid.UUID
    status: str


class TaskResponse(BaseModel):
    id: uuid.UUID
    prompt: str
    aspect_ratio: str
    status: str
    progress: int
    image_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
