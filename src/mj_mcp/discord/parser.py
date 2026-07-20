"""Midjourney message parser.

Extracts progress, completion status, image URLs, and button data
from Midjourney Bot Discord messages.
"""

import re
from typing import Any

PROGRESS_PATTERN = re.compile(r"\((\d+)%\)")
UPSCALE_BUTTON_PATTERN = re.compile(r"MJ::JOB::upsample::(\d+)::")
UPSCALE_INDEX_PATTERN = re.compile(r"Image #(\d+)")
# Pattern for animate/video buttons
ANIMATE_BUTTON_PATTERN = re.compile(r"(?i)MJ::JOB::animate|MJ::JOB::video|MJ::Job::animate|MJ::Job::video")


def extract_progress(content: str) -> int | None:
    match = PROGRESS_PATTERN.search(content)
    if match:
        return int(match.group(1))
    return None


def is_completed(message: Any) -> bool:
    return bool(message.attachments) and bool(message.components)


def extract_image_url(message: Any) -> str | None:
    if message.attachments:
        return message.attachments[0].url
    return None


def extract_all_image_urls(message: Any) -> list[str]:
    """Extract all image URLs from message attachments."""
    if message.attachments:
        return [a.url for a in message.attachments]
    return []


def extract_upscale_buttons(message: Any) -> dict[int, str]:
    """Extract U1-U4 button custom_ids from message components.

    Returns dict mapping upscale index (1-4) to custom_id string.
    """
    buttons: dict[int, str] = {}
    for row in getattr(message, "components", []):
        for child in getattr(row, "children", []):
            custom_id = getattr(child, "custom_id", None)
            if custom_id:
                match = UPSCALE_BUTTON_PATTERN.search(custom_id)
                if match:
                    buttons[int(match.group(1))] = custom_id
    return buttons


def extract_all_buttons(message: Any) -> dict[str, str]:
    """Extract ALL button custom_ids from message components.

    Returns dict mapping button label to custom_id.
    """
    buttons: dict[str, str] = {}
    for row in getattr(message, "components", []):
        for child in getattr(row, "children", []):
            custom_id = getattr(child, "custom_id", None)
            label = getattr(child, "label", None)
            if custom_id and label:
                buttons[label] = custom_id
            elif custom_id:
                # Fallback: use part of custom_id as label
                buttons[custom_id.split("::")[-1]] = custom_id
    return buttons


def is_grid_completion(message: Any) -> bool:
    """Check if message is a completed grid with U1-U4 upscale buttons."""
    if not is_completed(message):
        return False
    buttons = extract_upscale_buttons(message)
    return len(buttons) > 0


def is_single_image_completion(message: Any) -> bool:
    """Check if message is a completed single image (upscale/variation result)."""
    if not is_completed(message):
        return False
    if is_grid_completion(message):
        return False
    return len(message.attachments) == 1


def is_video_result(message: Any) -> bool:
    """Check if message contains a video result."""
    if not message.attachments:
        return False
    for a in message.attachments:
        if a.content_type and a.content_type.startswith("video/"):
            return True
    return False


def has_animate_button(message: Any) -> bool:
    """Check if message has an animate/video button."""
    for row in getattr(message, "components", []):
        for child in getattr(row, "children", []):
            custom_id = getattr(child, "custom_id", None)
            if custom_id and ANIMATE_BUTTON_PATTERN.search(custom_id):
                return True
    return False


def extract_upscale_index(content: str) -> int | None:
    """Extract upscale index N from 'Image #N' pattern."""
    match = UPSCALE_INDEX_PATTERN.search(content)
    if match:
        idx = int(match.group(1))
        if 1 <= idx <= 4:
            return idx
    return None


def parse_mj_message(message: Any) -> dict[str, Any]:
    completed = is_completed(message)
    progress = extract_progress(message.content)

    if completed:
        progress = 100

    return {
        "progress": progress,
        "completed": completed,
        "image_url": extract_image_url(message) if completed else None,
    }
