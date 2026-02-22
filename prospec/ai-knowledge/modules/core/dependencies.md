# Dependencies: core

<!-- prospec:auto-start -->

## Internal Imports

| From Module | What | Used In |
|-------------|------|---------|
| models | `Task`, `ApiKey`, `TaskStatus` | `concurrency.py` |
| services | `TaskService`, `UsageService`, `QuotaService` | `concurrency.py` |
| providers-discord | `CorrelationManager` | `concurrency.py` |
| providers (protocol) | `MidjourneyClient` | `concurrency.py` (type annotation) |

## Reverse Dependencies (Who Imports This Module)

| Module | What | Used For |
|--------|------|----------|
| infra | `ConcurrencyLimiter` | Lifespan startup, callback wiring |

## Third-Party Packages

| Package | Used For |
|---------|----------|
| `sqlalchemy` | async_sessionmaker, AsyncSession, select |

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
