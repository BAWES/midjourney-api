# Dependencies: infra

<!-- prospec:auto-start -->

## Internal Imports

| From Module | What | Used In |
|-------------|------|---------|
| api | `v1.router`, `set_dependencies` | `main.py` |
| core | `ConcurrencyLimiter` | `main.py` (lifespan) |
| providers-discord | `DiscordMidjourneyClient`, `CorrelationManager` | `main.py` (lifespan) |
| providers-mock | `MockMidjourneyClient` | `main.py` (lifespan) |
| models | All models | Alembic env.py |

## Reverse Dependencies (Who Imports This Module)

| Module | What | Used For |
|--------|------|----------|
| api | `get_db`, `settings` | DB session, config values |
| services | `settings` | Platform daily limit |

## Third-Party Packages

| Package | Used For |
|---------|----------|
| `fastapi` | FastAPI app, exception handlers, middleware |
| `sqlalchemy` | create_async_engine, async_sessionmaker |
| `pydantic-settings` | BaseSettings, env loading |
| `uvicorn` | ASGI server (run target) |

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
