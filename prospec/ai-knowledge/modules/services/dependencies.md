# Dependencies: services

<!-- prospec:auto-start -->

## Internal Imports

| From Module | What | Used In |
|-------------|------|---------|
| models | `Task`, `TaskStatus`, `ApiKey`, `QuotaUsage`, `UsageLog` | All services |
| models | `VALID_TRANSITIONS` (in task_service) | State machine validation |
| providers-discord | `CorrelationManager` | `imagine_service.py` |
| infra | `settings` | `quota_service.py` (platform_daily_limit) |

## Reverse Dependencies (Who Imports This Module)

| Module | What | Used For |
|--------|------|----------|
| api | `ImagineService`, `TaskService`, `QuotaService`, `UsageService` | Endpoint handlers |
| core | `TaskService`, `UsageService`, `QuotaService` | ConcurrencyLimiter callbacks |

## Third-Party Packages

| Package | Used For |
|---------|----------|
| `sqlalchemy` | select, func, text, AsyncSession |
| `sqlalchemy.exc` | OperationalError (advisory lock fallback) |
| `fastapi` | HTTPException (prompt validation) |

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
