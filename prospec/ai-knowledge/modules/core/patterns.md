# Patterns: core

<!-- prospec:auto-start -->

## Semaphore-Based Concurrency

```python
self._semaphore = asyncio.Semaphore(max_concurrent)

async def _dispatch_loop(self):
    while True:
        task_id = await self._dispatch_queue.get()
        await self._semaphore.acquire()
        asyncio.create_task(self._dispatch_wrapper(task_id))
```

## Semaphore Ownership

Only `_dispatch_wrapper` releases on dispatch failure; callbacks release on completion/error:

```python
async def _dispatch_wrapper(self, task_id):
    try:
        await self.dispatch_one(task_id)
    except Exception:
        self._semaphore.release()  # Release on dispatch failure only

async def on_complete(self, correlation_tag, image_url, **kwargs):
    # ... update DB ...
    self._semaphore.release()  # Release on completion
```

## Callback Registration

ConcurrencyLimiter registers itself as callback target on MidjourneyClient:

```python
self._mj_client.set_callbacks(
    on_progress=self.on_progress,
    on_complete=self.on_complete,
    on_error=self.on_error,
)
```

## Timeout Pattern

Background loop checks for stale tasks every 10 seconds:

```python
async def _timeout_loop(self):
    while True:
        await asyncio.sleep(10)
        await self.check_timeouts()

async def check_timeouts(self):
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._timeout_seconds)
    # Query PROCESSING tasks with updated_at < cutoff
    # Transition to FAILED, release semaphore
```

## Recovery on Startup

Rebuild in-memory state from database for crash recovery:

```python
async def recover(self):
    # Find PROCESSING tasks in DB
    # Rebuild correlation map
    # Adjust semaphore count
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
