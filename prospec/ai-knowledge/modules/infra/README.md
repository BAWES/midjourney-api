# Module: infra

> Infrastructure — configuration, database, logging, application bootstrap.

## Responsibilities

- Load configuration from environment variables and `.env` file
- Initialize async SQLAlchemy engine and session factory
- Configure structured JSON logging with correlation context
- Bootstrap FastAPI application with lifespan, middleware, exception handlers
- Conditionally instantiate Discord or Mock provider based on config

## Key Files

| File | Purpose |
|------|---------|
| `src/app/config.py` | Settings (pydantic-settings) — all environment config |
| `src/app/database.py` | Async engine + session factory + `get_db()` dependency |
| `src/app/logging_config.py` | JSONFormatter + `setup_logging()` |
| `src/app/main.py` | FastAPI app, lifespan (startup/shutdown), exception handlers |
| `src/app/exceptions.py` | Custom exception classes |
| `src/app/middleware/correlation_id.py` | X-Correlation-ID middleware |

## Public Interfaces

- `Settings` — Pydantic BaseSettings with all config fields
- `get_db() -> AsyncGenerator[AsyncSession, None]` — DB session dependency
- `setup_logging(level)` — Initialize JSON structured logging
- `app: FastAPI` — Application instance

## Dependencies

- **Internal**: api (router), core (ConcurrencyLimiter), providers (Discord/Mock), services (via DI)
- **External**: fastapi, sqlalchemy, pydantic-settings

## Design Decisions

- **Lifespan pattern**: `@asynccontextmanager` manages provider startup/shutdown, queue creation, limiter lifecycle
- **Conditional provider**: If `discord_bot_token` starts with `"mock"`, uses MockMidjourneyClient
- **Exception handlers**: TaskNotFoundError → 404, QuotaExceededError → 429, InvalidStateTransitionError → 409
- **Session config**: `expire_on_commit=False` to allow access after commit without refresh

<!-- prospec:user-start -->
<!-- prospec:user-end -->
