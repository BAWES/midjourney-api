# API Surface: services

<!-- prospec:auto-start -->

## Classes

### `ImagineService`
```python
class ImagineService:
    def __init__(
        self,
        db: AsyncSession,
        dispatch_queue: asyncio.Queue[uuid.UUID],
        correlation: CorrelationManager,
    ) -> None: ...

    @staticmethod
    def sanitize_prompt(prompt: str) -> str: ...

    async def submit(
        self,
        api_key: ApiKey,
        prompt: str,
        aspect_ratio: str = "1:1",
    ) -> Task: ...
```

### `TaskService`
```python
class TaskService:
    def __init__(self, db: AsyncSession) -> None: ...

    async def create_task(
        self,
        api_key_id: uuid.UUID,
        prompt: str,
        aspect_ratio: str = "1:1",
    ) -> Task: ...

    async def get_task(
        self,
        task_id: uuid.UUID,
        api_key_id: uuid.UUID,
    ) -> Task: ...

    async def get_task_by_id(self, task_id: uuid.UUID) -> Task: ...

    async def list_tasks(
        self,
        api_key_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]: ...

    async def transition(
        self,
        task_id: uuid.UUID,
        target_status: TaskStatus,
    ) -> Task: ...

    async def update_progress(self, task_id: uuid.UUID, progress: int) -> Task: ...
    async def update_image_url(self, task_id: uuid.UUID, image_url: str) -> Task: ...
    async def set_correlation_tag(self, task_id: uuid.UUID, tag: str) -> Task: ...
```

### `QuotaService`
```python
class QuotaService:
    def __init__(self, db: AsyncSession) -> None: ...

    async def check_and_deduct(self, api_key: ApiKey) -> bool: ...
    async def rollback(self, api_key: ApiKey) -> None: ...
    async def get_quota_info(self, api_key: ApiKey) -> dict: ...
```

### `UsageService`
```python
class UsageService:
    def __init__(self, db: AsyncSession) -> None: ...

    async def create_log(self, task: Task, api_key_id: uuid.UUID) -> UsageLog: ...

    async def list_logs(
        self,
        api_key_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[UsageLog], int]: ...
```

## Constants

### `VALID_TRANSITIONS`
```python
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.PROCESSING, TaskStatus.FAILED},
    TaskStatus.PROCESSING: {TaskStatus.SUCCESS, TaskStatus.FAILED},
    TaskStatus.SUCCESS: set(),
    TaskStatus.FAILED: set(),
}
```

### Regex Patterns
```python
_MJ_PARAM_PATTERN = re.compile(r"\s--\w+")
_CORRELATION_TAG_PATTERN = re.compile(r"mjr-[a-f0-9]+")
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
