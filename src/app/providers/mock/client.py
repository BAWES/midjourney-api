import asyncio
import uuid
from collections.abc import Callable, Coroutine


class MockMidjourneyClient:
    def __init__(self, delay: float = 1.0) -> None:
        self._delay = delay
        self._on_progress: Callable[..., Coroutine] | None = None
        self._on_complete: Callable[..., Coroutine] | None = None
        self._on_error: Callable[..., Coroutine] | None = None
        self._on_grid_complete: Callable[..., Coroutine] | None = None
        self._on_upscale_result: Callable[..., Coroutine] | None = None
        self._tasks: list[asyncio.Task] = []
        # Track upscale_count per correlation_tag for simulation
        self._upscale_counts: dict[str, int] = {}

    def set_callbacks(
        self,
        on_progress: Callable[..., Coroutine],
        on_complete: Callable[..., Coroutine],
        on_error: Callable[..., Coroutine],
        on_grid_complete: Callable[..., Coroutine],
        on_upscale_result: Callable[..., Coroutine],
    ) -> None:
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error
        self._on_grid_complete = on_grid_complete
        self._on_upscale_result = on_upscale_result

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

    async def upscale(
        self,
        message_id: str,
        custom_id: str,
    ) -> None:
        # No-op: mock results come from _simulate_generation
        pass

    def set_upscale_count(self, correlation_tag: str, count: int) -> None:
        """Set expected upscale count for a tag (called by ConcurrencyLimiter)."""
        self._upscale_counts[correlation_tag] = count

    async def _simulate_generation(self, correlation_tag: str) -> None:
        # Phase 1: Grid rendering progress
        progress_steps = [25, 50, 75, 100]
        for pct in progress_steps:
            await asyncio.sleep(self._delay / len(progress_steps))
            if self._on_progress:
                await self._on_progress(
                    correlation_tag=correlation_tag,
                    progress=pct,
                )

        # Phase 2: Grid completion with upscale buttons
        mock_message_id = str(uuid.uuid4())
        grid_url = f"https://cdn.midjourney.com/mock/{correlation_tag}/grid.png"
        upscale_buttons = {
            i: f"MJ::JOB::upsample::{i}::{uuid.uuid4()}"
            for i in range(1, 5)
        }

        if self._on_grid_complete:
            await self._on_grid_complete(
                correlation_tag=correlation_tag,
                image_url=grid_url,
                message_id=mock_message_id,
                upscale_buttons=upscale_buttons,
            )

        # Phase 3: Upscale results
        upscale_count = self._upscale_counts.get(correlation_tag, 1)
        for i in range(1, upscale_count + 1):
            await asyncio.sleep(self._delay / max(upscale_count, 1))
            if self._on_upscale_result:
                await self._on_upscale_result(
                    correlation_tag=correlation_tag,
                    image_url=f"https://cdn.midjourney.com/mock/{correlation_tag}/u{i}.png",
                    upscale_index=i,
                )
