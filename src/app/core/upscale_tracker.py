"""UpscaleTracker — in-memory state manager for upscale results per task."""

from dataclasses import dataclass, field


@dataclass
class UpscaleState:
    task_id: str
    upscale_count: int
    grid_image_url: str
    message_id: str
    button_custom_ids: dict[int, str]
    results: dict[int, str] = field(default_factory=dict)
    errors: dict[int, str] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return len(self.results) + len(self.errors) >= self.upscale_count

    @property
    def completed_count(self) -> int:
        return len(self.results) + len(self.errors)

    @property
    def success_count(self) -> int:
        return len(self.results)

    def get_image_urls(self) -> list[str]:
        """Return collected image URLs ordered by upscale index."""
        return [self.results[i] for i in sorted(self.results)]


class UpscaleTracker:
    def __init__(self) -> None:
        self._states: dict[str, UpscaleState] = {}

    def start(
        self,
        task_id: str,
        upscale_count: int,
        grid_image_url: str,
        message_id: str,
        button_custom_ids: dict[int, str],
    ) -> UpscaleState:
        state = UpscaleState(
            task_id=task_id,
            upscale_count=upscale_count,
            grid_image_url=grid_image_url,
            message_id=message_id,
            button_custom_ids=button_custom_ids,
        )
        self._states[task_id] = state
        return state

    def record_result(self, task_id: str, upscale_index: int, image_url: str) -> UpscaleState | None:
        state = self._states.get(task_id)
        if state is None:
            return None
        if upscale_index not in state.results:
            state.results[upscale_index] = image_url
        return state

    def record_error(self, task_id: str, upscale_index: int, error: str) -> UpscaleState | None:
        state = self._states.get(task_id)
        if state is None:
            return None
        if upscale_index not in state.errors:
            state.errors[upscale_index] = error
        return state

    def get(self, task_id: str) -> UpscaleState | None:
        return self._states.get(task_id)

    def remove(self, task_id: str) -> None:
        self._states.pop(task_id, None)
