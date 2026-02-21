"""Midjourney message parser.

Extracts progress percentage, completion status, and image URLs
from Midjourney Bot messages.
"""

import re
from typing import Any

PROGRESS_PATTERN = re.compile(r"\((\d+)%\)")


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
