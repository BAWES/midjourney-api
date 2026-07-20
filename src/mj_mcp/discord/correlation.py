"""Correlation tag strategy for matching MJ responses to tasks.

Embeds a unique tag (mjr-{16-hex-chars}) in the prompt. When Midjourney
echoes the prompt back, the tag is extracted and mapped to a task_id.
"""

import re
import secrets

TAG_PATTERN = re.compile(r"mjr-[a-f0-9]{16}")


class CorrelationManager:
    def __init__(self) -> None:
        self._tag_to_task: dict[str, str] = {}

    def generate_tag(self) -> str:
        return f"mjr-{secrets.token_hex(8)}"

    def embed_in_prompt(self, prompt: str, tag: str) -> str:
        return f"{tag} {prompt}"

    def extract_tag(self, text: str) -> str | None:
        match = TAG_PATTERN.search(text)
        if match:
            return match.group(0)
        return None

    def register(self, tag: str, task_id: str) -> None:
        self._tag_to_task[tag] = task_id

    def lookup(self, tag: str) -> str | None:
        return self._tag_to_task.get(tag)

    def unregister(self, tag: str) -> None:
        self._tag_to_task.pop(tag, None)
