# API Surface: models

<!-- prospec:auto-start -->

## Enums

### `TaskStatus`
```python
class TaskStatus(enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
```

## Mixins

### `TimestampMixin`
```python
class TimestampMixin:
    created_at: Mapped[datetime]   # server_default=func.now()
    updated_at: Mapped[datetime]   # server_default=func.now(), onupdate=func.now()
```

## ORM Models

### `Task`
```python
class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID]                  # PK, default=uuid4
    api_key_id: Mapped[uuid.UUID]          # FK -> api_keys.id
    prompt: Mapped[str]                    # Text
    aspect_ratio: Mapped[str]              # String(20), default="1:1"
    status: Mapped[TaskStatus]             # Enum, default=QUEUED
    progress: Mapped[int]                  # default=0
    image_url: Mapped[str | None]          # Text, nullable
    correlation_tag: Mapped[str | None]    # String(20), nullable
    error_message: Mapped[str | None]      # Text, nullable

    api_key: Mapped["ApiKey"]              # back_populates="tasks"
    usage_log: Mapped["UsageLog | None"]   # back_populates="task"
```
Indexes: `(api_key_id, created_at)`, `status`, `correlation_tag`

### `ApiKey`
```python
class ApiKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID]          # PK, default=uuid4
    name: Mapped[str]              # String(255)
    key_hash: Mapped[str]          # String(64), unique, indexed
    daily_limit: Mapped[int]       # default=50
    monthly_limit: Mapped[int]     # default=1000
    is_active: Mapped[bool]        # default=True

    tasks: Mapped[list["Task"]]
    quota_usages: Mapped[list["QuotaUsage"]]
```

### `QuotaUsage`
```python
class QuotaUsage(TimestampMixin, Base):
    __tablename__ = "quota_usages"

    id: Mapped[uuid.UUID]          # PK, default=uuid4
    api_key_id: Mapped[uuid.UUID]  # FK -> api_keys.id, indexed
    usage_date: Mapped[date]       # indexed
    daily_used: Mapped[int]        # default=0
```
Unique constraint: `(api_key_id, usage_date)`

### `UsageLog`
```python
class UsageLog(TimestampMixin, Base):
    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID]               # PK, default=uuid4
    task_id: Mapped[uuid.UUID]           # FK -> tasks.id, unique
    api_key_id: Mapped[uuid.UUID]        # FK -> api_keys.id
    prompt: Mapped[str]                  # Text
    aspect_ratio: Mapped[str]            # String(20)
    status: Mapped[str]                  # String(20)
    image_url: Mapped[str | None]        # Text, nullable
    duration_seconds: Mapped[float | None]  # Float, nullable
```
Indexes: `(api_key_id, created_at)`

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
