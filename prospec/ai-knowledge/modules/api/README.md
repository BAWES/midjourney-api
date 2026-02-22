# Module: api

> HTTP API layer — FastAPI routers, dependency injection, request/response handling.

## Responsibilities

- Expose REST API endpoints under `/api/v1/`
- Authenticate requests via `X-API-Key` header (HMAC-SHA256)
- Validate request bodies and query parameters (Pydantic)
- Delegate business logic to the services layer
- Return structured JSON responses with appropriate HTTP status codes

## Key Files

| File | Purpose |
|------|---------|
| `src/app/api/deps.py` | Shared dependencies: API key auth, DB session factory |
| `src/app/api/v1/imagine.py` | POST /imagine endpoint — submit generation tasks |
| `src/app/api/v1/tasks.py` | GET /tasks, GET /tasks/{id} — task status & listing |
| `src/app/api/v1/quota.py` | GET /quota — remaining quota info |
| `src/app/api/v1/usage.py` | GET /usage — usage history with date filtering |
| `src/app/api/v1/health.py` | GET /health — liveness check |
| `src/app/api/v1/router.py` | Aggregates all v1 sub-routers |

## Public Interfaces

- `hash_api_key(raw_key: str) -> str` — HMAC-SHA256 hashing
- `get_current_api_key(...)` — FastAPI dependency for auth
- `get_db_session()` — Async DB session generator
- `set_dependencies(dispatch_queue, correlation)` — Module-level DI for imagine endpoint

## Dependencies

- **Internal**: services (TaskService, QuotaService, UsageService, ImagineService), models (ApiKey), schemas (all)
- **External**: fastapi, sqlalchemy, pydantic

## Design Decisions

- **Module-level DI**: `imagine.py` uses `set_dependencies()` to receive dispatch_queue and correlation manager at startup, avoiding circular imports with the lifespan function
- **Ownership enforcement**: Task and usage queries always filter by `api_key_id` to prevent cross-tenant data access
- **Pagination**: Consistent `page`/`page_size` pattern across list endpoints with configurable limits

<!-- prospec:user-start -->
<!-- prospec:user-end -->
