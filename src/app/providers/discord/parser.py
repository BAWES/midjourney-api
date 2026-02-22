"""Midjourney message parser.

Extracts progress percentage, completion status, and image URLs
from Midjourney Bot messages.
"""

import re
from typing import Any

PROGRESS_PATTERN = re.compile(r"\((\d+)%\)")
UPSCALE_BUTTON_PATTERN = re.compile(r"MJ::JOB::upsample::(\d+)::")
UPSCALE_INDEX_PATTERN = re.compile(r"Image #(\d+)")


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


def extract_upscale_buttons(message: Any) -> dict[int, str]:
    """Extract U1-U4 button custom_ids from message components.

    Returns a dict mapping upscale index (1-4) to custom_id string.
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


def is_grid_completion(message: Any) -> bool:
    """Check if message is a completed grid with U1-U4 upscale buttons."""
    if not is_completed(message):
        return False
    buttons = extract_upscale_buttons(message)
    return len(buttons) > 0


def is_upscale_result(message: Any) -> bool:
    """Check if message is a completed upscale result (not a grid)."""
    return is_completed(message) and not is_grid_completion(message)


def extract_upscale_index(content: str) -> int | None:
    """Extract upscale index N from 'Image #N' pattern in content."""
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
