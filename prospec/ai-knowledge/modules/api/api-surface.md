# API Surface: api

<!-- prospec:auto-start -->

## Functions

### `hash_api_key`
```python
def hash_api_key(raw_key: str) -> str
```
HMAC-SHA256 hash of raw API key using `settings.api_key_secret`.

### `get_current_api_key`
```python
async def get_current_api_key(
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> ApiKey
```
FastAPI dependency — extracts `X-API-Key` header, hashes it, queries DB for active key. Raises HTTP 401 if invalid.

### `get_db_session`
```python
async def get_db_session() -> AsyncGenerator[AsyncSession, None]
```
Yields async DB session from `get_db()`.

### `set_dependencies`
```python
def set_dependencies(
    dispatch_queue: asyncio.Queue[uuid.UUID],
    correlation: CorrelationManager,
) -> None
```
Module-level injection for imagine endpoint. Called during app lifespan startup.

## Schemas (Request/Response)

### `ImagineRequest`
```python
class ImagineRequest(BaseModel):
    prompt: str          # min_length=1, max_length=4000
    aspect_ratio: str    # pattern=r"^\d+:\d+$", default="1:1"
```

### `ImagineResponse`
```python
class ImagineResponse(BaseModel):
    task_id: uuid.UUID
    status: Literal["queued"] = "queued"
```

### `TaskResponse`
```python
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
```

### `TaskListResponse`
```python
class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
```

### `QuotaResponse`
```python
class QuotaResponse(BaseModel):
    daily_remaining: int
    daily_limit: int
    monthly_remaining: int
    monthly_limit: int
    platform_daily_remaining: int
```

### `UsageLogResponse`
```python
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
```

### `UsageListResponse`
```python
class UsageListResponse(BaseModel):
    items: list[UsageLogResponse]
    total: int
    page: int
    page_size: int
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
