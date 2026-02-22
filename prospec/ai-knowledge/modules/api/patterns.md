# Patterns: api

<!-- prospec:auto-start -->

## Dependency Injection

All endpoints use FastAPI `Depends()` for auth and DB:

```python
async def imagine(
    body: ImagineRequest,
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> ImagineResponse:
```

## Module-Level DI

The imagine endpoint uses a global injection pattern to avoid circular imports:

```python
_dispatch_queue: asyncio.Queue[uuid.UUID] | None = None
_correlation: CorrelationManager | None = None

def set_dependencies(dispatch_queue, correlation):
    global _dispatch_queue, _correlation
    _dispatch_queue = dispatch_queue
    _correlation = correlation
```

## Service Instantiation

Services are created per-request inside handlers:

```python
svc = TaskService(db)
task = await svc.get_task(task_id, api_key_id=api_key.id)
```

## Pagination Pattern

Consistent across list endpoints:

```python
page: int = Query(default=1, ge=1)
page_size: int = Query(default=20, ge=1, le=100)
```

Response wraps items with metadata:
```python
TaskListResponse(items=items, total=total, page=page, page_size=page_size)
```

## Auth Pattern

Header extraction → hash → DB lookup → active check:

```python
key_hash = hash_api_key(raw_key)
result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True))
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
