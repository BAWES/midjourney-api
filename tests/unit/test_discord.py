"""Tests for MJ message parser and correlation tag strategy."""

from dataclasses import dataclass, field

import pytest

from app.providers.discord.parser import (
    extract_progress,
    is_completed,
    extract_image_url,
    parse_mj_message,
)
from app.providers.discord.correlation import CorrelationManager


# --- Fake discord.Message-like objects for testing ---


@dataclass
class FakeAttachment:
    url: str
    width: int | None = None
    height: int | None = None


@dataclass
class FakeComponent:
    children: list = field(default_factory=list)


@dataclass
class FakeMessage:
    content: str
    attachments: list[FakeAttachment] = field(default_factory=list)
    components: list[FakeComponent] = field(default_factory=list)


# === Parser Tests ===


class TestExtractProgress:
    def test_progress_25(self) -> None:
        assert extract_progress("**a cat** - (25%) <@123>") == 25

    def test_progress_50(self) -> None:
        assert extract_progress("**a cat** - (50%) <@123>") == 50

    def test_progress_100(self) -> None:
        assert extract_progress("**a cat** - (100%) <@123>") == 100

    def test_no_progress(self) -> None:
        assert extract_progress("**a cat** - Image #1 <@123>") is None

    def test_progress_zero(self) -> None:
        assert extract_progress("**a cat** - (0%) <@123>") == 0

    def test_progress_in_complex_message(self) -> None:
        msg = "**a sunset over mountains mjr-abc12345** - (75%) (fast, stealth)"
        assert extract_progress(msg) == 75


class TestIsCompleted:
    def test_completed_with_attachments_and_components(self) -> None:
        msg = FakeMessage(
            content="**a cat** - Image #1",
            attachments=[FakeAttachment(url="https://cdn.example.com/img.png")],
            components=[FakeComponent()],
        )
        assert is_completed(msg) is True

    def test_not_completed_no_attachments(self) -> None:
        msg = FakeMessage(content="**a cat** - (50%)")
        assert is_completed(msg) is False

    def test_not_completed_no_components(self) -> None:
        msg = FakeMessage(
            content="**a cat**",
            attachments=[FakeAttachment(url="https://cdn.example.com/img.png")],
        )
        assert is_completed(msg) is False


class TestExtractImageUrl:
    def test_extract_from_attachment(self) -> None:
        msg = FakeMessage(
            content="done",
            attachments=[
                FakeAttachment(
                    url="https://cdn.discordapp.com/attachments/123/456/image.png",
                    width=1024,
                    height=1024,
                )
            ],
        )
        assert extract_image_url(msg) == "https://cdn.discordapp.com/attachments/123/456/image.png"

    def test_no_attachments(self) -> None:
        msg = FakeMessage(content="no image")
        assert extract_image_url(msg) is None


class TestParseMjMessage:
    def test_parse_progress_message(self) -> None:
        msg = FakeMessage(content="**a cat mjr-abc12345** - (50%) (fast)")
        result = parse_mj_message(msg)
        assert result["progress"] == 50
        assert result["completed"] is False
        assert result["image_url"] is None

    def test_parse_completed_message(self) -> None:
        msg = FakeMessage(
            content="**a cat mjr-abc12345** - Image #1",
            attachments=[FakeAttachment(url="https://cdn.example.com/final.png", width=1024, height=1024)],
            components=[FakeComponent()],
        )
        result = parse_mj_message(msg)
        assert result["completed"] is True
        assert result["image_url"] == "https://cdn.example.com/final.png"
        assert result["progress"] == 100


# === Correlation Tag Tests ===


class TestCorrelationManager:
    def test_generate_tag(self) -> None:
        mgr = CorrelationManager()
        tag = mgr.generate_tag()
        assert tag.startswith("mjr-")
        assert len(tag) == 12  # "mjr-" + 8 hex chars

    def test_embed_tag_in_prompt(self) -> None:
        mgr = CorrelationManager()
        tag = mgr.generate_tag()
        result = mgr.embed_in_prompt("a beautiful sunset", tag)
        assert tag in result
        assert "a beautiful sunset" in result

    def test_extract_tag_from_text(self) -> None:
        mgr = CorrelationManager()
        tag = "mjr-abc12345"
        text = f"**a beautiful sunset {tag}** - (50%)"
        assert mgr.extract_tag(text) == tag

    def test_extract_tag_not_found(self) -> None:
        mgr = CorrelationManager()
        assert mgr.extract_tag("**a cat** - (50%)") is None

    def test_register_and_lookup(self) -> None:
        mgr = CorrelationManager()
        tag = "mjr-test1234"
        task_id = "some-task-uuid"
        mgr.register(tag, task_id)
        assert mgr.lookup(tag) == task_id

    def test_lookup_unknown_tag(self) -> None:
        mgr = CorrelationManager()
        assert mgr.lookup("mjr-unknown1") is None

    def test_unregister(self) -> None:
        mgr = CorrelationManager()
        mgr.register("mjr-test1234", "task-1")
        mgr.unregister("mjr-test1234")
        assert mgr.lookup("mjr-test1234") is None

    def test_roundtrip_embed_extract(self) -> None:
        mgr = CorrelationManager()
        tag = mgr.generate_tag()
        prompt = mgr.embed_in_prompt("a cat on a roof", tag)
        extracted = mgr.extract_tag(prompt)
        assert extracted == tag
