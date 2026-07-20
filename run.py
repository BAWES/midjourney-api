#!/usr/bin/env python3
"""Midjourney MCP Server — run with: python run.py"""
import sys
from pathlib import Path

_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from mj_mcp.server import (
    mcp, HOST, PORT, BEARER_TOKEN,
    logger, start_backend, stop_backend,
)


def main():
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    # Auth middleware
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

    # Build ASGI app
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware)

    # Start backend inside uvicorn's own event loop via startup event
    @app.on_event("startup")
    async def _start():
        await start_backend()

    @app.on_event("shutdown")
    async def _stop():
        await stop_backend()

    print(f"[MJ-MCP] Starting on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
