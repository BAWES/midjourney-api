# Dependencies: api

<!-- prospec:auto-start -->

## Internal Imports

| From Module | What | Used In |
|-------------|------|---------|
| models | `ApiKey` | `deps.py` (auth query) |
| models | `TaskStatus` | — |
| schemas | `ImagineRequest`, `ImagineResponse` | `imagine.py` |
| schemas | `TaskResponse`, `TaskListResponse` | `tasks.py` |
| schemas | `QuotaResponse` | `quota.py` |
| schemas | `UsageLogResponse`, `UsageListResponse` | `usage.py` |
| services | `ImagineService` | `imagine.py` |
| services | `TaskService` | `tasks.py` |
| services | `QuotaService` | `quota.py` |
| services | `UsageService` | `usage.py` |
| providers-discord | `CorrelationManager` | `imagine.py` (via set_dependencies) |
| infra | `get_db`, `settings` | `deps.py` |

## Reverse Dependencies (Who Imports This Module)

| Module | What | Used For |
|--------|------|----------|
| infra | `v1.router` | Router inclusion in FastAPI app |
| infra | `set_dependencies` | Lifespan startup DI |

## Third-Party Packages

| Package | Used For |
|---------|----------|
| `fastapi` | APIRouter, Depends, HTTPException, Query, status |
| `sqlalchemy` | select, AsyncSession |
| `pydantic` | BaseModel (via schemas) |

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
