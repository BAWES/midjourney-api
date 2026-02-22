# Patterns: infra

<!-- prospec:auto-start -->

## Lifespan Context Manager

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    dispatch_queue = asyncio.Queue()
    # Create provider (conditional)
    if settings.discord_bot_token.startswith("mock"):
        mj_client = MockMidjourneyClient()
    else:
        mj_client = DiscordMidjourneyClient(...)
    # Wire components
    limiter = ConcurrencyLimiter(async_session, mj_client, correlation, dispatch_queue)
    mj_client.set_callbacks(limiter.on_progress, limiter.on_complete, limiter.on_error)
    set_dependencies(dispatch_queue, correlation)
    # Start
    await mj_client.start()
    await limiter.start()
    yield
    # Shutdown
    await limiter.stop()
    await mj_client.stop()
```

## Exception Handlers

Map custom exceptions to HTTP status codes:

```python
@app.exception_handler(TaskNotFoundError)
async def handle_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(QuotaExceededError)
async def handle_quota(request, exc):
    return JSONResponse(status_code=429, content={"detail": str(exc)})
```

## Structured JSON Logging

```python
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        return json.dumps(log_data)
```

## Environment-Based Configuration

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
