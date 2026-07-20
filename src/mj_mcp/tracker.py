"""In-memory task tracker for Midjourney generations.

Manages active task states with correlation tags, message IDs,
button data, and results. Thread-safe via asyncio.Lock.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    GRID_COMPLETE = "grid_complete"
    UPSCALING = "upscaling"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskState:
    id: str  # our internal task id (uuid4)
    prompt: str
    aspect_ratio: str
    correlation_tag: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0

    # Discord references
    message_id: str = ""
    upscale_buttons: dict[int, str] = field(default_factory=dict)
    all_buttons: dict[str, str] = field(default_factory=dict)

    # Results
    grid_url: str = ""
    image_urls: list[str] = field(default_factory=list)
    video_url: str = ""

    # Timing
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    # Events for async wait
    grid_event: asyncio.Event = field(default_factory=asyncio.Event)
    complete_event: asyncio.Event = field(default_factory=asyncio.Event)
    error_message: str = ""


class TaskTracker:
    """In-memory task store. Thread-safe via asyncio.Lock."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: dict[str, TaskState] = {}  # task_id -> state
        self._correlation_to_task: dict[str, str] = {}  # tag -> task_id

    async def create_task(self, prompt: str, aspect_ratio: str) -> TaskState:
        task_id = str(uuid.uuid4())
        state = TaskState(
            id=task_id,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
        )
        async with self._lock:
            self._tasks[task_id] = state
        return state

    async def get_task(self, task_id: str) -> TaskState | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def set_correlation(self, task_id: str, tag: str) -> None:
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.correlation_tag = tag
                self._correlation_to_task[tag] = task_id

    async def lookup_by_tag(self, tag: str) -> TaskState | None:
        async with self._lock:
            task_id = self._correlation_to_task.get(tag)
            if task_id:
                return self._tasks.get(task_id)
            return None

    async def update_progress(self, task_id: str, progress: int) -> None:
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.progress = progress
                if state.status == TaskStatus.PENDING:
                    state.status = TaskStatus.PROCESSING

    async def set_grid_complete(
        self,
        task_id: str,
        grid_url: str,
        message_id: str,
        upscale_buttons: dict[int, str],
        all_buttons: dict[str, str],
        has_animate: bool = False,
    ) -> None:
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.grid_url = grid_url
                state.message_id = message_id
                state.upscale_buttons = upscale_buttons
                state.all_buttons = all_buttons
                state.status = TaskStatus.GRID_COMPLETE
                state.progress = 100
                state.grid_event.set()

    async def set_complete(self, task_id: str, image_urls: list[str]) -> None:
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.image_urls = image_urls
                state.status = TaskStatus.COMPLETED
                state.completed_at = time.time()
                state.complete_event.set()

    async def set_video_complete(self, task_id: str, video_url: str) -> None:
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.video_url = video_url
                state.image_urls = [video_url]
                state.status = TaskStatus.COMPLETED
                state.completed_at = time.time()
                state.complete_event.set()

    async def set_failed(self, task_id: str, error: str) -> None:
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.status = TaskStatus.FAILED
                state.error_message = error
                state.completed_at = time.time()
                state.grid_event.set()
                state.complete_event.set()

    async def remove(self, task_id: str) -> None:
        async with self._lock:
            state = self._tasks.pop(task_id, None)
            if state and state.correlation_tag:
                self._correlation_to_task.pop(state.correlation_tag, None)

    def to_result(self, state: TaskState) -> dict:
        """Serialize task state for tool response."""
        return {
            "task_id": state.id,
            "status": state.status.value,
            "progress": state.progress,
            "prompt": state.prompt,
            "aspect_ratio": state.aspect_ratio,
            "grid_url": state.grid_url,
            "image_urls": state.image_urls,
            "video_url": state.video_url,
            "message_id": state.message_id,
            "upscale_buttons": list(state.upscale_buttons.keys()),
            "has_animate_button": "Animate" in state.all_buttons or bool(state.all_buttons),
            "error": state.error_message or None,
            "created_at": state.created_at,
            "completed_at": state.completed_at or None,
        }
