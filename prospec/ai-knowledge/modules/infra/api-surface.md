# API Surface: infra

<!-- prospec:auto-start -->

## Configuration

### `Settings`
```python
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://..."
    discord_bot_token: str = ""
    discord_user_token: str = ""
    mj_channel_id: str = ""
    mj_max_concurrent_jobs: int = 3
    mj_task_timeout_seconds: int = 120
    platform_daily_limit: int = 100
    api_key_secret: str = "change-me-in-production"
    api_v1_prefix: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env")
```

### `settings`
```python
settings = Settings()  # Module-level singleton
```

## Database

### `engine`
```python
engine: AsyncEngine  # create_async_engine(settings.database_url)
```

### `async_session`
```python
async_session: async_sessionmaker[AsyncSession]  # expire_on_commit=False
```

### `get_db`
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]: ...
```

## Logging

### `JSONFormatter`
```python
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str: ...
```
Outputs JSON with: timestamp, level, logger, message, correlation_id, task_id, exception.

### `setup_logging`
```python
def setup_logging(level: str = "INFO") -> None: ...
```

## Application

### `lifespan`
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]: ...
```

### `app`
```python
app = FastAPI(title="Midjourney Relay API", lifespan=lifespan)
```

## Exceptions

```python
class TaskNotFoundError(Exception): ...         # -> HTTP 404
class QuotaExceededError(Exception): ...        # -> HTTP 429
class InvalidStateTransitionError(Exception): ... # -> HTTP 409
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
