import asyncio
from collections.abc import Callable, Coroutine


class MockMidjourneyClient:
    def __init__(self, delay: float = 1.0) -> None:
        self._delay = delay
        self._on_progress: Callable[..., Coroutine] | None = None
        self._on_complete: Callable[..., Coroutine] | None = None
        self._on_error: Callable[..., Coroutine] | None = None
        self._tasks: list[asyncio.Task] = []

    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine],
        on_complete: Callable[..., Coroutine],
        on_error: Callable[..., Coroutine],
    ) -> None:
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._tasks.clear()

    async def imagine(
        self,
        prompt: str,
        aspect_ratio: str,
        correlation_tag: str,
    ) -> None:
        task = asyncio.create_task(
            self._simulate_generation(correlation_tag)
        )
        self._tasks.append(task)

    async def _simulate_generation(self, correlation_tag: str) -> None:
        progress_steps = [25, 50, 75, 100]
        for pct in progress_steps:
            await asyncio.sleep(self._delay / len(progress_steps))
            if self._on_progress:
                await self._on_progress(
                    correlation_tag=correlation_tag,
                    progress=pct,
                )

        if self._on_complete:
            await self._on_complete(
                correlation_tag=correlation_tag,
                image_url=f"https://cdn.midjourney.com/mock/{correlation_tag}.png",
            )
