# Module: core

> Core orchestration — concurrency control, task dispatch, timeout management.

## Responsibilities

- Limit concurrent Midjourney jobs via asyncio.Semaphore
- Consume dispatch queue and send jobs to MidjourneyClient
- Handle provider callbacks (progress, complete, error) and update database
- Check for timed-out tasks and transition them to FAILED
- Recover limiter state from database on startup
- Orchestrate upscale phase (grid → U1-U4 button clicks → collect results)
- Track upscale results via UpscaleTracker

## Key Files

| File | Purpose |
|------|---------|
| `src/app/core/concurrency.py` | ConcurrencyLimiter — semaphore, dispatch loop, callbacks, timeouts |
| `src/app/core/dispatch.py` | DispatchQueue type alias and helpers |
| `src/app/core/upscale_tracker.py` | UpscaleTracker for managing per-task upscale state |

## Public Interfaces

- `ConcurrencyLimiter(session_factory, mj_client, correlation, dispatch_queue, max_concurrent, timeout_seconds, upscale_timeout_seconds)`
- `dispatch_one(task_id)` — fetch task, transition to PROCESSING, call `mj_client.imagine()`
- `on_progress(correlation_tag, progress)` — update task progress
- `on_complete(correlation_tag, image_url)` — transition to SUCCESS, create usage log, release semaphore
- `on_error(correlation_tag, error_message)` — transition to FAILED, rollback quota, release semaphore
- `on_grid_complete(correlation_tag, image_url, message_id, upscale_buttons)` — transition to UPSCALING, register tracker, send button click interactions
- `on_upscale_result(correlation_tag, image_url, upscale_index)` — record upscale result, finalize task when all expected results collected
- `check_timeouts()` — dual query for PROCESSING + UPSCALING tasks; fail stale tasks in either state
- `recover()` — rebuild in-memory state from PROCESSING tasks in DB; UPSCALING tasks marked FAILED on restart

## Dependencies

- **Internal**: services (TaskService, UsageService, QuotaService), models (TaskStatus, Task, ApiKey), providers/protocol (MidjourneyClient)
- **External**: asyncio, sqlalchemy

## Design Decisions

- **Semaphore ownership**: Only `_dispatch_wrapper` releases semaphore on dispatch failure; `on_complete`/`on_error` release on completion
- **Re-raise on failure**: `dispatch_one` re-raises exceptions after transitioning to FAILED, so wrapper can handle semaphore
- **Background tasks**: Dispatch runs as asyncio.Task with `add_done_callback` for cleanup
- **10s timeout loop**: Periodic check compares `updated_at` against `timeout_seconds` config
- **Atomic pop() on UpscaleTracker**: Prevents double finalization race when multiple upscale results arrive concurrently
- **Semaphore held through upscale phase**: Conservative MVP approach — semaphore is not released until all upscales complete

<!-- prospec:user-start -->
<!-- prospec:user-end -->
