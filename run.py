#!/usr/bin/env python3
"""Midjourney MCP Server — run with: python run.py"""
import sys
from pathlib import Path

_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from mj_mcp.server import (
    mcp, HOST, PORT, BEARER_TOKEN,
    logger, _ready, _start_time,
    start_backend, stop_backend,
)


async def serve():
    import time as t
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class BearerAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.method == "OPTIONS":
                return await call_next(request)
            if request.url.path == "/health":
                return await call_next(request)
            if not BEARER_TOKEN:
                return await call_next(request)

            auth = request.headers.get("x-api-key", "") or request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                token = auth.removeprefix("Bearer ")
            else:
                token = auth
            if not token:
                return JSONResponse({"error": "Missing auth"}, status_code=401)
            if token != BEARER_TOKEN:
                return JSONResponse({"error": "Invalid token"}, status_code=403)
            return await call_next(request)

    # Build MCP ASGI app
    mcp_app = mcp.streamable_http_app()
    mcp_app.add_middleware(BearerAuthMiddleware)

    # Mount everything under a single Starlette app with health endpoint
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    async def health_endpoint(request):
        return JSONResponse({
            "status": "ok" if _ready else "warming",
            "gateway_connected": _ready,
            "uptime_seconds": int(t.time() - _start_time),
        })

    app = Starlette(routes=[
        Route("/health", endpoint=health_endpoint, methods=["GET"]),
        Mount("/", app=mcp_app),
    ])

    # Start backend on the same event loop
    await start_backend()

    print(f"[MJ-MCP] Starting on http://{HOST}:{PORT}")
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        await stop_backend()


if __name__ == "__main__":
    import asyncio
    asyncio.run(serve())
