# Module: models

> Data layer — SQLAlchemy ORM models, Pydantic schemas, enums.

## Responsibilities

- Define database table schemas via SQLAlchemy 2.x Mapped columns
- Define Pydantic request/response schemas for API validation
- Provide shared enums (TaskStatus) and mixins (TimestampMixin)
- Enforce database constraints (unique, foreign key, indexes)

## Key Files

| File | Purpose |
|------|---------|
| `src/app/models/base.py` | Base class, TimestampMixin, TaskStatus enum |
| `src/app/models/task.py` | Task + UsageLog ORM models |
| `src/app/models/api_key.py` | ApiKey + QuotaUsage ORM models |
| `src/app/models/quota.py` | QuotaUsage (re-export from api_key) |
| `src/app/models/usage_log.py` | UsageLog (re-export from task) |
| `src/app/schemas/task.py` | ImagineRequest, ImagineResponse, TaskResponse, TaskListResponse |
| `src/app/schemas/usage.py` | UsageLogResponse, UsageListResponse |
| `src/app/schemas/quota.py` | QuotaResponse |

## Public Interfaces

### ORM Models
- `Task` — Generation task with lifecycle tracking (status, progress, image_url, image_urls, upscale_count)
  - `image_urls: Mapped[list | None]` — JSON column, nullable; stores collected upscale result URLs
  - `upscale_count: Mapped[int]` — default 1; number of upscale variants to generate
- `ApiKey` — API key with daily/monthly limits
- `QuotaUsage` — Per-key daily usage counter
- `UsageLog` — Immutable audit log of completed tasks

### Enums
- `TaskStatus` — QUEUED, PROCESSING, UPSCALING, SUCCESS, FAILED

### Schemas
- `ImagineRequest` — prompt (1-4000 chars), aspect_ratio (regex validated), `upscale_count: int = Field(default=1, ge=1, le=4)`
- `TaskResponse` — ORM-compatible response with `from_attributes=True`; includes `image_urls: list[str] | None = None` and `upscale_count: int = 1`

## Dependencies

- **Internal**: None (leaf module)
- **External**: sqlalchemy, pydantic

## Design Decisions

- **UUID primary keys**: All tables use `uuid.uuid4()` for globally unique IDs
- **TimestampMixin**: Centralized `created_at`/`updated_at` with server-side defaults
- **Composite indexes**: `(api_key_id, created_at)` for common query patterns
- **One-to-one UsageLog**: Unique constraint on `task_id` ensures one log per task

<!-- prospec:user-start -->
<!-- prospec:user-end -->
