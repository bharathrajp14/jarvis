# api/server.py — Modular FastAPI Application Factory for BR JARVIS
"""
Modular FastAPI Application Factory for BR JARVIS Autonomous Control Plane.
Mounts all route routers with authentication, CORS, rate limiting, and lifespan management.
"""
from __future__ import annotations

import os
import re
import sys
import hmac
import json
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Set

import uvicorn
from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.bootstrap import build_assistant_runtime
from agent.task_queue import get_queue
from agent.recovery_watchdog import get_recovery_watchdog
from orchestrator import JarvisOrchestrator

from api.routes.health import router as health_router
from api.routes.tasks import router as tasks_router
from api.routes.devices import router as devices_router
from api.routes.routines import router as routines_router
from api.routes.skills import router as skills_router
from api.routes.connectors import router as connectors_router
from api.routes.memory import router as memory_router
from api.routes.chat import router as chat_router
from api.routes.voice import router as voice_router
from api.routes.websocket import router as ws_router

from api.state import (
    BASE_DIR,
    CONFIG_DIR,
    API_FILE,
    WEB_DIR,
    SERVER_API_KEY,
    ACTIVE_WEBSOCKETS,
    get_ws_lock,
    get_orchestrator,
    set_orchestrator,
)

logger = logging.getLogger("JARVIS.API.Server")


# ── Rich markup stripper & WS stdout broadcast ──────────────────────────────
_RICH_RE = re.compile(r'\[/?[a-z_]+\]', re.IGNORECASE)


def strip_rich(text: str) -> str:
    return _RICH_RE.sub('', text)


class WSBroadcastStream:
    def __init__(self, original):
        self.original = original
        self._active = False
        self._loop: asyncio.AbstractEventLoop | None = None

    def activate(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._active = True

    def deactivate(self) -> None:
        self._active = False
        self._loop = None

    def write(self, text):
        try:
            self.original.write(text)
        except UnicodeEncodeError:
            try:
                self.original.write(text.encode('utf-8', errors='replace').decode('utf-8'))
            except Exception:
                pass
        if self._active and self._loop and self._loop.is_running() and text.strip():
            clean = strip_rich(text.strip())
            if clean:
                asyncio.run_coroutine_threadsafe(broadcast_log(clean), self._loop)

    def flush(self):
        self.original.flush()

    def isatty(self):
        return hasattr(self.original, 'isatty') and self.original.isatty()


ws_stream = WSBroadcastStream(sys.stdout)
sys.stdout = ws_stream


async def _send_ws_log(ws: WebSocket, line: str):
    try:
        from starlette.websockets import WebSocketState
        if ws.client_state == WebSocketState.CONNECTED:
            await asyncio.wait_for(ws.send_json({"type": "log", "message": line}), timeout=0.5)
    except Exception:
        async with get_ws_lock():
            ACTIVE_WEBSOCKETS.discard(ws)


async def broadcast_log(line: str):
    async with get_ws_lock():
        targets = list(ACTIVE_WEBSOCKETS)
    for ws in targets:
        asyncio.create_task(_send_ws_log(ws, line))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler — builds runtime, recovers tasks, and activates logging."""
    logger.info("⚙ Starting BR JARVIS Core Server...")

    runtime = await asyncio.to_thread(build_assistant_runtime)
    set_orchestrator(runtime.orchestrator)
    get_queue()

    # Run Crash Recovery Watchdog
    try:
        get_recovery_watchdog().inspect_and_recover()
    except Exception as exc:
        logger.warning("Recovery watchdog non-fatal note: %s", exc)

    ws_stream.activate(asyncio.get_running_loop())
    logger.info("✓ BR JARVIS Core Server Ready.")
    yield
    # Shutdown
    ws_stream.deactivate()
    orch = get_orchestrator()
    if orch:
        try:
            orch.shutdown()
        except Exception:
            pass


def create_app() -> FastAPI:
    """Create and configure the production FastAPI application."""
    app = FastAPI(
        title="BR JARVIS Autonomous Operating Platform",
        version="38.5.0",
        description="Local-First Autonomous AI Control Plane & Device Orchestrator",
        lifespan=lifespan
    )

    # CORS configuration
    cors_origins = os.environ.get("JARVIS_CORS_ORIGINS", "").strip()
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if cors_origins:
        allowed_origins.extend([o.strip() for o in cors_origins.split(",") if o.strip()])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Key Authentication Middleware
    @app.middleware("http")
    async def verify_api_key(request: Request, call_next):
        if SERVER_API_KEY:
            if request.url.path.startswith(("/api", "/v1")) and request.url.path not in ("/api/health", "/health"):
                auth_header = request.headers.get("Authorization")
                api_key_header = request.headers.get("X-API-Key")
                token = None
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                elif api_key_header:
                    token = api_key_header
                if not token or not hmac.compare_digest(token, SERVER_API_KEY):
                    return JSONResponse(status_code=401, content={"detail": "Unauthorized: Invalid API Key"})
        return await call_next(request)

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(exc)})

    # 404 Exception Handler with Glassmorphic Web Fallback
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            accept = request.headers.get("accept", "")
            if "text/html" in accept and not request.url.path.startswith(("/api", "/v1", "/ws")):
                index_file = WEB_DIR / "index.html"
                if index_file.exists() and request.url.path not in ("/404", "/404.html"):
                    return FileResponse(index_file)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # Mount Route Routers
    app.include_router(health_router)
    app.include_router(tasks_router)
    app.include_router(devices_router)
    app.include_router(routines_router)
    app.include_router(skills_router)
    app.include_router(connectors_router)
    app.include_router(memory_router)
    app.include_router(chat_router)
    app.include_router(voice_router)
    app.include_router(ws_router)

    # Mount Static Files & Web Client
    @app.get("/")
    @app.get("/index.html")
    @app.get("/web")
    @app.get("/web/")
    @app.get("/web/index.html")
    async def get_index():
        index_file = WEB_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>BR JARVIS Dashboard</h1><p>Web client loaded</p>")

    @app.get("/galaxy")
    @app.get("/galaxy.html")
    @app.get("/3d")
    async def get_galaxy():
        galaxy_file = WEB_DIR / "galaxy.html"
        if galaxy_file.exists():
            return FileResponse(galaxy_file)
        return HTMLResponse("<h1>3D Knowledge Galaxy</h1>")

    app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

    @app.get("/{file_name:path}")
    async def serve_root_static_or_fallback(file_name: str, request: Request):
        if file_name.startswith(("api/", "v1/", "ws", "health")):
            raise HTTPException(status_code=404, detail=f"API endpoint '/{file_name}' not found.")
        target_file = WEB_DIR / file_name
        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)
        accept = request.headers.get("accept", "")
        if "text/html" in accept or not Path(file_name).suffix:
            index_file = WEB_DIR / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
        raise HTTPException(status_code=404, detail=f"Requested URL '/{file_name}' not found.")

    return app
