# API Surface: core

<!-- prospec:auto-start -->

## Classes

### `ConcurrencyLimiter`
```python
class ConcurrencyLimiter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mj_client: MidjourneyClient,
        correlation: CorrelationManager,
        dispatch_queue: asyncio.Queue[uuid.UUID],
        max_concurrent: int = 3,
        timeout_seconds: int = 120,
    ) -> None: ...

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def dispatch_one(self, task_id: uuid.UUID) -> None: ...

    # Callbacks (registered on MidjourneyClient)
    async def on_progress(self, correlation_tag: str, progress: int, **kwargs: object) -> None: ...
    async def on_complete(self, correlation_tag: str, image_url: str, **kwargs: object) -> None: ...
    async def on_error(self, correlation_tag: str, error_message: str, **kwargs: object) -> None: ...

    async def check_timeouts(self) -> None: ...
    async def recover(self) -> None: ...
```

### Internal Methods

```python
async def _dispatch_wrapper(self, task_id: uuid.UUID) -> None: ...
async def _dispatch_loop(self) -> None: ...
async def _timeout_loop(self) -> None: ...
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
