"""Simple current task tracker.

Since imagine calls are rate-limited (3s gap) and deduplicated,
only one imagine call is active at a time. The gateway routes all
MJ bot messages to the current task by channel order.

No correlation tags in prompts — messages are matched by their
Discord message_id chain and arrival order.
"""

_current_task_id: str | None = None
_current_task_message_ids: set[str] = set()
_message_to_task: dict[str, str] = {}

# Rate limiting
_last_imagine_time: float = 0.0
MIN_IMAGINE_GAP: float = 3.0


def set_current(task_id: str) -> None:
    global _current_task_id
    _current_task_id = task_id


def get_current() -> str | None:
    return _current_task_id


def clear() -> None:
    global _current_task_id, _current_task_message_ids, _message_to_task
    _current_task_id = None
    _current_task_message_ids.clear()
    _message_to_task.clear()


def track_message(message_id: str, task_id: str | None = None) -> None:
    """Track a message_id as belonging to a task."""
    tid = task_id or _current_task_id
    if tid:
        _current_task_message_ids.add(message_id)
        _message_to_task[message_id] = tid


def lookup_task(message_id: str) -> str | None:
    """Look up which task a message_id belongs to."""
    return _message_to_task.get(message_id)


def is_tracked(message_id: str) -> bool:
    return message_id in _current_task_message_ids


def check_rate_limit() -> float | None:
    """Returns None if OK, or seconds to wait if rate limited."""
    import time
    global _last_imagine_time
    elapsed = time.time() - _last_imagine_time
    if elapsed < MIN_IMAGINE_GAP:
        return MIN_IMAGINE_GAP - elapsed
    return None


def update_last_imagine_time() -> None:
    global _last_imagine_time
    import time
    _last_imagine_time = time.time()
