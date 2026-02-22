# Patterns: services

<!-- prospec:auto-start -->

## State Machine

Task transitions enforced via dictionary lookup:

```python
VALID_TRANSITIONS = {
    TaskStatus.QUEUED: {TaskStatus.PROCESSING, TaskStatus.FAILED},
    TaskStatus.PROCESSING: {TaskStatus.SUCCESS, TaskStatus.FAILED},
    TaskStatus.SUCCESS: set(),
    TaskStatus.FAILED: set(),
}

async def transition(self, task_id, target_status):
    task = await self.get_task_by_id(task_id)
    if target_status not in VALID_TRANSITIONS[task.status]:
        raise InvalidStateTransitionError(...)
    task.status = target_status
```

## Atomic Quota Check-and-Deduct

Row lock first, then aggregate checks within the same transaction:

```python
# 1. Row lock
existing = await db.execute(
    select(QuotaUsage).where(...).with_for_update()
)
# 2. Check daily
# 3. Check monthly (within lock)
# 4. Advisory lock for platform-wide check
try:
    await db.execute(text("SELECT pg_advisory_xact_lock(0)"))
except SAOperationalError:
    pass  # SQLite fallback
# 5. Deduct
```

## Service Composition

ImagineService composes other services:

```python
class ImagineService:
    async def submit(self, api_key, prompt, aspect_ratio):
        prompt = self.sanitize_prompt(prompt)
        quota_svc = QuotaService(self._db)
        if not await quota_svc.check_and_deduct(api_key):
            raise QuotaExceededError()
        task_svc = TaskService(self._db)
        task = await task_svc.create_task(...)
```

## Input Validation at Service Boundary

```python
@staticmethod
def sanitize_prompt(prompt: str) -> str:
    if _CORRELATION_TAG_PATTERN.search(prompt):
        raise HTTPException(status_code=400, detail="...")
    return _MJ_PARAM_PATTERN.sub("", prompt).strip()
```

## Commit-then-Refresh

All mutations follow: modify → commit → refresh:

```python
task.status = target_status
await self._db.commit()
await self._db.refresh(task)
return task
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
