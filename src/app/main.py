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

    from app.api.v1.imagine import set_dependencies
    from app.providers.discord.correlation import CorrelationManager

    setup_logging()

    dispatch_queue: asyncio.Queue = asyncio.Queue()
    correlation = CorrelationManager()
    set_dependencies(dispatch_queue, correlation)

    yield
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
