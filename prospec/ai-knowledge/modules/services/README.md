# Module: services

> Business logic layer — orchestration, quota enforcement, task lifecycle, usage tracking.

## Responsibilities

- Orchestrate the imagine workflow (sanitize → quota → create → enqueue)
- Enforce task state machine transitions
- Perform atomic quota check-and-deduct with concurrency safety
- Create immutable usage logs on task completion
- Provide paginated query interfaces for tasks and usage

## Key Files

| File | Purpose |
|------|---------|
| `src/app/services/imagine_service.py` | Orchestrates submission: sanitize prompt, check quota, create task, enqueue |
| `src/app/services/task_service.py` | Task CRUD + state machine transitions |
| `src/app/services/quota_service.py` | Three-tier quota enforcement with row-level + advisory locking |
| `src/app/services/usage_service.py` | Usage log creation and paginated retrieval |

## Public Interfaces

- `ImagineService.submit(api_key, prompt, aspect_ratio) -> Task`
- `ImagineService.sanitize_prompt(prompt) -> str` (static)
- `TaskService.create_task(prompt, aspect_ratio, api_key_id, upscale_count: int = 1) -> Task` — creates task with optional upscale_count
- `TaskService.transition(task_id, target_status) -> Task`
- `TaskService.update_image_urls(task_id, image_urls) -> Task` — persists collected upscale result URLs to the task record
- `QuotaService.check_and_deduct(api_key) -> bool`
- `UsageService.create_log(task, api_key_id) -> UsageLog`

## Dependencies

- **Internal**: models (Task, ApiKey, QuotaUsage, UsageLog, TaskStatus), providers-discord (CorrelationManager)
- **External**: sqlalchemy, fastapi (HTTPException)

## Design Decisions

- **State machine validation**: `VALID_TRANSITIONS` dict prevents invalid status changes; raises `InvalidStateTransitionError`; now includes UPSCALING transitions (e.g. PROCESSING → UPSCALING, UPSCALING → SUCCESS, UPSCALING → FAILED)
- **TOCTOU prevention**: QuotaService uses `SELECT FOR UPDATE` row locks + `pg_advisory_xact_lock(0)` for platform-wide limits
- **SQLite fallback**: Advisory lock wrapped in try/except for test compatibility
- **Prompt sanitization**: Strips `--param` flags and rejects `mjr-*` correlation tag injection at service boundary

<!-- prospec:user-start -->
<!-- prospec:user-end -->
