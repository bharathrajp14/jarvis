# api/state.py — Shared Server State & Runtime Resolvers
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Set

from starlette.websockets import WebSocket

from brjarvis.core.paths import paths
from brjarvis.orchestrator import JarvisOrchestrator

logger = logging.getLogger("JARVIS.API.State")

BASE_DIR = paths.PROJECT_ROOT
CONFIG_DIR = paths.CONFIG_ROOT
API_FILE = CONFIG_DIR / "api_keys.json"
try:
    from dotenv import load_dotenv

    load_dotenv(paths.DOTENV_FILE, override=False)
except ImportError:
    pass
WEB_DIR = Path(__file__).resolve().parents[1] / "static"

ORCHESTRATOR: Optional[JarvisOrchestrator] = None
ACTIVE_WEBSOCKETS: Set[WebSocket] = set()
WEBSOCKETS_LOCK: Optional[asyncio.Lock] = None

# Server API Key
_MIN_SERVER_API_KEY_LENGTH = 24


def _load_server_api_key() -> Optional[str]:
    """Load the canonical server key without silently accepting weak placeholders."""
    key = os.environ.get("JARVIS_SERVER_API_KEY") or os.environ.get("SERVER_API_KEY")
    if not key and API_FILE.exists():
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8"))
            key = data.get("server_api_key")
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Unable to read server API key configuration: %s", exc)
    if not key:
        return None
    normalized = str(key).strip()
    is_placeholder = normalized.lower().startswith(("replace_with", "your_", "changeme", "example"))
    if is_placeholder or len(normalized) < _MIN_SERVER_API_KEY_LENGTH:
        logger.warning(
            "JARVIS_SERVER_API_KEY is unset or uses a placeholder/weak key. "
            "Production control plane endpoints will require a secure key (>=24 chars)."
        )
        return None
    return normalized


SERVER_API_KEY = _load_server_api_key()


def require_server_api_key() -> str:
    """Fail closed when the control-plane authentication key is unavailable."""
    key = _load_server_api_key()
    if not key:
        raise RuntimeError(
            "JARVIS_SERVER_API_KEY must be configured with a unique token (>=24 chars) "
            "before the web control plane can start. Copy .env.template to .env and generate a key."
        )
    return key


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
            from brjarvis.core.bootstrap import build_assistant_runtime
            runtime = build_assistant_runtime()
            ORCHESTRATOR = runtime.orchestrator
        except Exception as e:
            logger.debug("Lazy orchestrator initialization note: %s", e)
    return ORCHESTRATOR


def set_orchestrator(orchestrator: JarvisOrchestrator) -> None:
    """Explicitly set the active Orchestrator singleton."""
    global ORCHESTRATOR
    ORCHESTRATOR = orchestrator
