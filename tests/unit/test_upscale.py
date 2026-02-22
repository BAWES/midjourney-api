"""Tests for upscale feature: parser functions, UpscaleTracker, and ConcurrencyLimiter orchestration."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.upscale_tracker import UpscaleState, UpscaleTracker
from app.models.api_key import ApiKey
from app.models.base import TaskStatus
from app.providers.discord.correlation import CorrelationManager
from app.providers.discord.parser import (
    extract_upscale_buttons,
    extract_upscale_index,
    is_grid_completion,
    is_upscale_result,
)
from app.services.task_service import TaskService
from app.core.concurrency import ConcurrencyLimiter


# --- Fake discord.Message-like objects ---


@dataclass
class FakeAttachment:
    url: str


@dataclass
class FakeButton:
    custom_id: str | None = None
    label: str = ""


@dataclass
class FakeActionRow:
    children: list[FakeButton] = field(default_factory=list)


@dataclass
class FakeMessage:
    content: str
    attachments: list[FakeAttachment] = field(default_factory=list)
    components: list[FakeActionRow] = field(default_factory=list)


def make_grid_message(tag: str = "mjr-test1234") -> FakeMessage:
    """Create a realistic grid completion message with U1-U4 buttons."""
    buttons = [
        FakeButton(custom_id=f"MJ::JOB::upsample::{i}::fake-uuid-{i}", label=f"U{i}")
        for i in range(1, 5)
    ]
    # Add other buttons (V1-V4, etc.)
    buttons.extend([
        FakeButton(custom_id=f"MJ::JOB::variation::{i}::fake-uuid-v{i}", label=f"V{i}")
        for i in range(1, 5)
    ])
    return FakeMessage(
        content=f"**a cat {tag}** - Image #1",
        attachments=[FakeAttachment(url="https://cdn.example.com/grid.png")],
        components=[FakeActionRow(children=buttons[:4]), FakeActionRow(children=buttons[4:])],
    )


def make_upscale_result_message(tag: str = "mjr-test1234", index: int = 1) -> FakeMessage:
    """Create a realistic upscale result message (no U1-U4 buttons)."""
    return FakeMessage(
        content=f"**a cat {tag}** - Image #{index}",
        attachments=[FakeAttachment(url=f"https://cdn.example.com/u{index}.png")],
        components=[FakeActionRow(children=[
            FakeButton(custom_id="MJ::JOB::variation::1::other", label="V1"),
        ])],
    )


# === Parser Tests ===


class TestExtractUpscaleButtons:
    def test_extract_u1_to_u4(self) -> None:
        msg = make_grid_message()
        buttons = extract_upscale_buttons(msg)
        assert len(buttons) == 4
        assert 1 in buttons and 2 in buttons and 3 in buttons and 4 in buttons
        assert "upsample::1::" in buttons[1]

    def test_no_upscale_buttons(self) -> None:
        msg = FakeMessage(
            content="done",
            attachments=[FakeAttachment(url="https://example.com/img.png")],
            components=[FakeActionRow(children=[
                FakeButton(custom_id="MJ::JOB::variation::1::uuid", label="V1"),
            ])],
        )
        buttons = extract_upscale_buttons(msg)
        assert len(buttons) == 0

    def test_empty_components(self) -> None:
        msg = FakeMessage(content="test", attachments=[], components=[])
        assert extract_upscale_buttons(msg) == {}


class TestIsGridCompletion:
    def test_grid_with_upscale_buttons(self) -> None:
        msg = make_grid_message()
        assert is_grid_completion(msg) is True

    def test_upscale_result_not_grid(self) -> None:
        msg = make_upscale_result_message()
        assert is_grid_completion(msg) is False

    def test_progress_message_not_grid(self) -> None:
        msg = FakeMessage(content="**a cat** - (50%)")
        assert is_grid_completion(msg) is False


class TestIsUpscaleResult:
    def test_upscale_result(self) -> None:
        msg = make_upscale_result_message()
        assert is_upscale_result(msg) is True

    def test_grid_not_upscale_result(self) -> None:
        msg = make_grid_message()
        assert is_upscale_result(msg) is False

    def test_progress_not_upscale_result(self) -> None:
        msg = FakeMessage(content="**a cat** - (50%)")
        assert is_upscale_result(msg) is False


class TestExtractUpscaleIndex:
    def test_extract_index_1(self) -> None:
        assert extract_upscale_index("**a cat** - Image #1") == 1

    def test_extract_index_4(self) -> None:
        assert extract_upscale_index("**a cat** - Image #4") == 4

    def test_no_index(self) -> None:
        assert extract_upscale_index("**a cat** - (50%)") is None

    def test_index_out_of_range(self) -> None:
        assert extract_upscale_index("**a cat** - Image #5") is None

    def test_index_zero(self) -> None:
        assert extract_upscale_index("**a cat** - Image #0") is None


# === UpscaleTracker Tests ===


class TestUpscaleTracker:
    def test_start_creates_state(self) -> None:
        tracker = UpscaleTracker()
        state = tracker.start("task-1", 4, "grid.png", "msg-1", {1: "id1", 2: "id2", 3: "id3", 4: "id4"})
        assert state.task_id == "task-1"
        assert state.upscale_count == 4
        assert not state.is_complete

    def test_record_result(self) -> None:
        tracker = UpscaleTracker()
        tracker.start("task-1", 2, "grid.png", "msg-1", {1: "id1", 2: "id2"})
        state = tracker.record_result("task-1", 1, "https://u1.png")
        assert state is not None
        assert state.success_count == 1
        assert not state.is_complete

    def test_record_error(self) -> None:
        tracker = UpscaleTracker()
        tracker.start("task-1", 1, "grid.png", "msg-1", {1: "id1"})
        state = tracker.record_error("task-1", 1, "timeout")
        assert state is not None
        assert state.is_complete
        assert state.success_count == 0

    def test_is_complete_all_results(self) -> None:
        tracker = UpscaleTracker()
        tracker.start("task-1", 2, "grid.png", "msg-1", {1: "id1", 2: "id2"})
        tracker.record_result("task-1", 1, "u1.png")
        state = tracker.record_result("task-1", 2, "u2.png")
        assert state.is_complete
        assert state.success_count == 2

    def test_get_image_urls_ordered(self) -> None:
        tracker = UpscaleTracker()
        tracker.start("task-1", 3, "grid.png", "msg-1", {1: "id1", 2: "id2", 3: "id3"})
        tracker.record_result("task-1", 3, "u3.png")
        tracker.record_result("task-1", 1, "u1.png")
        tracker.record_result("task-1", 2, "u2.png")
        state = tracker.get("task-1")
        assert state.get_image_urls() == ["u1.png", "u2.png", "u3.png"]

    def test_record_unknown_task(self) -> None:
        tracker = UpscaleTracker()
        assert tracker.record_result("unknown", 1, "url") is None

    def test_remove(self) -> None:
        tracker = UpscaleTracker()
        tracker.start("task-1", 1, "grid.png", "msg-1", {1: "id1"})
        tracker.remove("task-1")
        assert tracker.get("task-1") is None

    def test_duplicate_result_ignored(self) -> None:
        tracker = UpscaleTracker()
        tracker.start("task-1", 1, "grid.png", "msg-1", {1: "id1"})
        tracker.record_result("task-1", 1, "first.png")
        tracker.record_result("task-1", 1, "duplicate.png")
        state = tracker.get("task-1")
        assert state.results[1] == "first.png"

    def test_mixed_results_and_errors(self) -> None:
        tracker = UpscaleTracker()
        tracker.start("task-1", 4, "grid.png", "msg-1", {1: "id1", 2: "id2", 3: "id3", 4: "id4"})
        tracker.record_result("task-1", 1, "u1.png")
        tracker.record_result("task-1", 2, "u2.png")
        tracker.record_result("task-1", 3, "u3.png")
        tracker.record_error("task-1", 4, "failed")
        state = tracker.get("task-1")
        assert state.is_complete
        assert state.success_count == 3
        assert len(state.errors) == 1
        assert state.get_image_urls() == ["u1.png", "u2.png", "u3.png"]


# === ConcurrencyLimiter Upscale Orchestration Tests ===


def _make_limiter(
    session_factory: async_sessionmaker,
    correlation: CorrelationManager,
) -> ConcurrencyLimiter:
    mock_client = AsyncMock()
    mock_client.upscale = AsyncMock()
    queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
    return ConcurrencyLimiter(
        session_factory=session_factory,
        mj_client=mock_client,
        correlation=correlation,
        dispatch_queue=queue,
        upscale_timeout_seconds=180,
    )


class TestConcurrencyLimiterGridComplete:
    async def test_grid_complete_transitions_to_upscaling(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=2)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        correlation = CorrelationManager()
        tag = "mjr-grid1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        upscale_buttons = {1: "MJ::upsample::1::uuid", 2: "MJ::upsample::2::uuid", 3: "MJ::upsample::3::uuid", 4: "MJ::upsample::4::uuid"}
        await limiter.on_grid_complete(
            correlation_tag=tag,
            image_url="https://grid.png",
            message_id="msg-123",
            upscale_buttons=upscale_buttons,
        )

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.UPSCALING
        assert refreshed.image_url == "https://grid.png"

    async def test_grid_complete_sends_upscale_interactions(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=2)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        correlation = CorrelationManager()
        tag = "mjr-grid5678"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        upscale_buttons = {1: "btn1", 2: "btn2", 3: "btn3", 4: "btn4"}
        await limiter.on_grid_complete(
            correlation_tag=tag,
            image_url="https://grid.png",
            message_id="msg-456",
            upscale_buttons=upscale_buttons,
        )

        # Should call upscale for U1 and U2 only (upscale_count=2)
        assert limiter._mj_client.upscale.call_count == 2

    async def test_grid_complete_does_not_release_semaphore(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=1)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        correlation = CorrelationManager()
        tag = "mjr-sem12345"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        initial_value = limiter._semaphore._value

        upscale_buttons = {1: "btn1", 2: "btn2", 3: "btn3", 4: "btn4"}
        await limiter.on_grid_complete(
            correlation_tag=tag,
            image_url="https://grid.png",
            message_id="msg-789",
            upscale_buttons=upscale_buttons,
        )

        # Semaphore should NOT be released
        assert limiter._semaphore._value == initial_value


class TestConcurrencyLimiterUpscaleResult:
    async def test_upscale_result_records_and_completes(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=1)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)
        correlation = CorrelationManager()
        tag = "mjr-res12345"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        # Manually register tracker
        limiter._upscale_tracker.start(
            task_id=str(task_id),
            upscale_count=1,
            grid_image_url="grid.png",
            message_id="msg-1",
            button_custom_ids={1: "btn1"},
        )

        await limiter.on_upscale_result(
            correlation_tag=tag,
            image_url="https://u1.png",
            upscale_index=1,
        )

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.SUCCESS
        assert refreshed.image_urls == ["https://u1.png"]

    async def test_upscale_4_results_all_success(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=4)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)
        correlation = CorrelationManager()
        tag = "mjr-4res1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        limiter._upscale_tracker.start(
            task_id=str(task_id),
            upscale_count=4,
            grid_image_url="grid.png",
            message_id="msg-1",
            button_custom_ids={1: "btn1", 2: "btn2", 3: "btn3", 4: "btn4"},
        )

        for i in range(1, 5):
            await limiter.on_upscale_result(
                correlation_tag=tag,
                image_url=f"https://u{i}.png",
                upscale_index=i,
            )

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.SUCCESS
        assert refreshed.image_urls == ["https://u1.png", "https://u2.png", "https://u3.png", "https://u4.png"]

    async def test_upscale_releases_semaphore_on_complete(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=1)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)
        correlation = CorrelationManager()
        tag = "mjr-sem56789"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        initial_value = limiter._semaphore._value
        limiter._upscale_tracker.start(
            task_id=str(task_id),
            upscale_count=1,
            grid_image_url="grid.png",
            message_id="msg-1",
            button_custom_ids={1: "btn1"},
        )

        await limiter.on_upscale_result(
            correlation_tag=tag,
            image_url="https://u1.png",
            upscale_index=1,
        )

        # Semaphore should be released
        assert limiter._semaphore._value == initial_value + 1


class TestConcurrencyLimiterPartialFailure:
    async def test_3_success_1_error_still_success(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=4)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)
        correlation = CorrelationManager()
        tag = "mjr-part1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        limiter._upscale_tracker.start(
            task_id=str(task_id),
            upscale_count=4,
            grid_image_url="grid.png",
            message_id="msg-1",
            button_custom_ids={1: "btn1", 2: "btn2", 3: "btn3", 4: "btn4"},
        )

        # 3 success, 1 error
        for i in range(1, 4):
            await limiter.on_upscale_result(
                correlation_tag=tag,
                image_url=f"https://u{i}.png",
                upscale_index=i,
            )
        # Record error for U4 directly in tracker, then trigger finalize via another result
        limiter._upscale_tracker.record_error(str(task_id), 4, "timeout")
        # State is now complete, call finalize
        await limiter._finalize_upscale(tag, str(task_id))

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.SUCCESS
        assert refreshed.image_urls == ["https://u1.png", "https://u2.png", "https://u3.png"]

    async def test_all_failed_transitions_to_failed(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=2)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)
        correlation = CorrelationManager()
        tag = "mjr-fail1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        limiter._upscale_tracker.start(
            task_id=str(task_id),
            upscale_count=2,
            grid_image_url="grid.png",
            message_id="msg-1",
            button_custom_ids={1: "btn1", 2: "btn2"},
        )

        limiter._upscale_tracker.record_error(str(task_id), 1, "error1")
        limiter._upscale_tracker.record_error(str(task_id), 2, "error2")
        await limiter._finalize_upscale(tag, str(task_id))

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.FAILED


class TestConcurrencyLimiterUpscaleTimeout:
    async def test_upscale_timeout_transitions_to_failed(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=4)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)

        # Set updated_at to past
        task.updated_at = datetime.now(timezone.utc) - timedelta(seconds=200)
        await db.commit()

        correlation = CorrelationManager()
        tag = "mjr-tout1234"
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)
        limiter._upscale_timeout = 180

        # Register partial results
        limiter._upscale_tracker.start(
            task_id=str(task_id),
            upscale_count=4,
            grid_image_url="grid.png",
            message_id="msg-1",
            button_custom_ids={1: "b1", 2: "b2", 3: "b3", 4: "b4"},
        )
        limiter._upscale_tracker.record_result(str(task_id), 1, "https://u1.png")

        await limiter.check_timeouts()

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.FAILED
        assert refreshed.image_urls == ["https://u1.png"]


class TestConcurrencyLimiterProgressFilter:
    async def test_progress_ignored_during_upscaling(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=1)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)
        await task_svc.update_progress(task_id, 50)

        correlation = CorrelationManager()
        tag = "mjr-prog1234"
        await task_svc.set_correlation_tag(task_id, tag)
        correlation.register(tag, str(task_id))

        limiter = _make_limiter(session_factory, correlation)

        # This should be ignored during UPSCALING
        await limiter.on_progress(correlation_tag=tag, progress=75)

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        # Progress should remain at 50, not 75
        assert refreshed.progress == 50


class TestConcurrencyLimiterRecover:
    async def test_recover_upscaling_tasks_marked_failed(
        self, session_factory: async_sessionmaker, db: AsyncSession, api_key: ApiKey
    ) -> None:
        task_svc = TaskService(db)
        task = await task_svc.create_task(api_key.id, "test", "1:1", upscale_count=4)
        task_id = task.id
        await task_svc.transition(task_id, TaskStatus.PROCESSING)
        await task_svc.transition(task_id, TaskStatus.UPSCALING)

        correlation = CorrelationManager()
        mock_client = AsyncMock()
        queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()

        limiter = ConcurrencyLimiter(
            session_factory=session_factory,
            mj_client=mock_client,
            correlation=correlation,
            dispatch_queue=queue,
        )
        await limiter.recover()

        db.expire_all()
        refreshed = await task_svc.get_task_by_id(task_id)
        assert refreshed.status == TaskStatus.FAILED
        assert "server restart" in refreshed.error_message
