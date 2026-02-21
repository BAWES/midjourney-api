class QuotaExceededError(Exception):
    def __init__(self, message: str = "Quota exceeded") -> None:
        self.message = message
        super().__init__(self.message)


class InvalidStateTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        self.message = f"Invalid state transition: {current} -> {target}"
        super().__init__(self.message)


class TaskNotFoundError(Exception):
    def __init__(self, task_id: str) -> None:
        self.message = f"Task not found: {task_id}"
        super().__init__(self.message)
