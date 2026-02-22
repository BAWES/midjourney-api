from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging import setup_logging
from app.database import engine
from app.exceptions import QuotaExceededError, TaskNotFoundError
from app.middleware.correlation_id import CorrelationIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    import asyncio
    import logging

    from app.api.v1.imagine import set_dependencies
    from app.core.concurrency import ConcurrencyLimiter
    from app.database import async_session
    from app.providers.discord.correlation import CorrelationManager

    log = logging.getLogger(__name__)
    setup_logging()

    dispatch_queue: asyncio.Queue = asyncio.Queue()
    correlation = CorrelationManager()
    set_dependencies(dispatch_queue, correlation)

    # Choose provider based on config
    if settings.discord_bot_token and settings.discord_user_token:
        from app.providers.discord.client import DiscordMidjourneyClient

        mj_client = DiscordMidjourneyClient(
            bot_token=settings.discord_bot_token,
            user_token=settings.discord_user_token,
            channel_id=settings.mj_channel_id,
            correlation=correlation,
        )
        log.info("Using DiscordMidjourneyClient")
    else:
        from app.providers.mock.client import MockMidjourneyClient

        mj_client = MockMidjourneyClient(delay=2.0)
        log.info("Discord tokens not configured — using MockMidjourneyClient")

    limiter = ConcurrencyLimiter(
        session_factory=async_session,
        mj_client=mj_client,
        correlation=correlation,
        dispatch_queue=dispatch_queue,
        max_concurrent=settings.mj_max_concurrent_jobs,
        timeout_seconds=settings.mj_task_timeout_seconds,
    )

    await mj_client.start()
    await limiter.start()

    yield

    await limiter.stop()
    await mj_client.stop()
    await engine.dispose()


app = FastAPI(title="Midjourney Relay API", version="0.1.0", lifespan=lifespan)

app.add_middleware(CorrelationIdMiddleware)


# Exception handlers
@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(QuotaExceededError)
async def quota_exceeded_handler(request: Request, exc: QuotaExceededError) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": exc.message})


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Include v1 API routes
from app.api.v1.router import router as v1_router  # noqa: E402

app.include_router(v1_router, prefix=settings.api_v1_prefix)
