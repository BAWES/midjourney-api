# Dependencies: models

<!-- prospec:auto-start -->

## Internal Imports

None — this is a leaf module with no internal dependencies.

## Reverse Dependencies (Who Imports This Module)

| Module | What | Used For |
|--------|------|----------|
| api | `ApiKey` | Auth dependency |
| services | `Task`, `ApiKey`, `QuotaUsage`, `UsageLog`, `TaskStatus` | Business logic |
| core | `Task`, `ApiKey`, `TaskStatus` | Concurrency + dispatch |
| infra | All models | Alembic migrations, lifespan |

## Third-Party Packages

| Package | Used For |
|---------|----------|
| `sqlalchemy` | DeclarativeBase, Mapped, mapped_column, relationship, ForeignKey |
| `sqlalchemy.ext.asyncio` | AsyncAttrs |
| `pydantic` | BaseModel (schemas) |

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
