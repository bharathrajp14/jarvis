# api/state.py — Shared Server State & Runtime Resolvers
from __future__ import annotations

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Set, Optional
from starlette.websockets import WebSocket
from orchestrator import JarvisOrchestrator

logger = logging.getLogger("JARVIS.API.State")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
API_FILE = CONFIG_DIR / "api_keys.json"
WEB_DIR = BASE_DIR / "web"

ORCHESTRATOR: Optional[JarvisOrchestrator] = None
ACTIVE_WEBSOCKETS: Set[WebSocket] = set()
WEBSOCKETS_LOCK: Optional[asyncio.Lock] = None

# Server API Key
SERVER_API_KEY = os.environ.get("JARVIS_SERVER_API_KEY")
if not SERVER_API_KEY and API_FILE.exists():
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        SERVER_API_KEY = data.get("server_api_key")
    except Exception:
        pass


def get_ws_lock() -> asyncio.Lock:
    global WEBSOCKETS_LOCK
    if WEBSOCKETS_LOCK is None:
        WEBSOCKETS_LOCK = asyncio.Lock()
    return WEBSOCKETS_LOCK


def get_orchestrator() -> Optional[JarvisOrchestrator]:
    """Return the active Orchestrator singleton, lazily initializing if needed."""
    global ORCHESTRATOR
    if ORCHESTRATOR is None:
        try:
            from core.bootstrap import build_assistant_runtime
            runtime = build_assistant_runtime()
            ORCHESTRATOR = runtime.orchestrator
        except Exception as e:
            logger.debug("Lazy orchestrator initialization note: %s", e)
    return ORCHESTRATOR


def set_orchestrator(orchestrator: JarvisOrchestrator) -> None:
    """Explicitly set the active Orchestrator singleton."""
    global ORCHESTRATOR
    ORCHESTRATOR = orchestrator
