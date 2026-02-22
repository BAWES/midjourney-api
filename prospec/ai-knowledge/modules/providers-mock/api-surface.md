# API Surface: providers-mock

<!-- prospec:auto-start -->

## Classes

### `MockMidjourneyClient`
```python
class MockMidjourneyClient:
    def __init__(self, delay: float = 1.0) -> None: ...

    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine],
        on_complete: Callable[..., Coroutine],
        on_error: Callable[..., Coroutine],
    ) -> None: ...

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def imagine(
        self,
        prompt: str,
        aspect_ratio: str,
        correlation_tag: str,
    ) -> None: ...
```

Implements `MidjourneyClient` Protocol.

### Internal

```python
async def _simulate_generation(self, correlation_tag: str) -> None
```
Emits progress at 25/50/75/100%, then calls `on_complete` with mock URL.

## Constants

Mock image URL template: `https://cdn.midjourney.com/mock/{correlation_tag}.png`

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
