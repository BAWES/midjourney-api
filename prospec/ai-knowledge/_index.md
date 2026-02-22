# AI Knowledge Index

> This index helps AI Agents quickly understand the project structure.
> Read this file first, then load specific module READMEs as needed.

## Modules

<!-- prospec:auto-start -->

| Module | Keywords | Status | Description | Files | Depends On |
|--------|----------|--------|-------------|-------|------------|
| api | endpoints, routes, auth, REST, FastAPI | Active | HTTP API layer — routers, dependency injection, request/response | readme, api-surface, dependencies, patterns, endpoints | models, services, providers-discord, infra |
| models | ORM, schema, database, Pydantic, SQLAlchemy | Active | Data layer — SQLAlchemy models, Pydantic schemas, enums | readme, api-surface, dependencies, patterns | — |
| services | business-logic, quota, task, usage, orchestration | Active | Business logic — imagine workflow, state machine, quota enforcement | readme, api-surface, dependencies, patterns | models, providers-discord, infra |
| providers-discord | Discord, gateway, interaction, correlation, parser | Active | Discord provider — /imagine commands, WebSocket monitoring, tag correlation | readme, api-surface, dependencies, patterns | — |
| providers-mock | mock, testing, simulation | Active | Mock provider — simulated MJ generation for testing without Discord | readme, api-surface, dependencies, patterns | — |
| core | concurrency, semaphore, dispatch, timeout, recovery | Active | Core orchestration — concurrency limiter, dispatch loop, timeout management | readme, api-surface, dependencies, patterns | models, services, providers-discord |
| infra | config, database, logging, FastAPI, lifespan | Active | Infrastructure — configuration, DB, logging, app bootstrap | readme, api-surface, dependencies, patterns | api, core, providers-discord, providers-mock, models |

<!-- prospec:auto-end -->

## Project Info

- **Language**: Python (FastAPI)
- **Knowledge Base**: `prospec/ai-knowledge/`
- **Constitution**: `prospec/CONSTITUTION.md`

## How to Use

1. Start by reading this index to understand available modules
2. Load the specific module's `README.md` for detailed information
3. Check `_conventions.md` for coding patterns and standards
4. Consult `CONSTITUTION.md` for architectural constraints
5. Use `module-map.yaml` for dependency relationships
