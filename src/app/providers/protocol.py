from typing import Protocol, runtime_checkable
from collections.abc import Callable, Coroutine


@runtime_checkable
class MidjourneyClient(Protocol):
    async def imagine(
        self,
        prompt: str,
        aspect_ratio: str,
        correlation_tag: str,
    ) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine],
        on_complete: Callable[..., Coroutine],
        on_error: Callable[..., Coroutine],
    ) -> None: ...
