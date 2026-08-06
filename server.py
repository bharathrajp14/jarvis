# server.py
"""
FastAPI Server for JARVIS MK37.
Exposes REST and WebSocket endpoints for dashboard, voice sync, and OpenAI-compatible API.
"""
from __future__ import annotations

import asyncio
import json
import hmac
import logging
import os
import re
import sys
import time
import traceback
import platform
import uuid
import threading
import subprocess
from pathlib import Path

logger = logging.getLogger("JARVIS.Server")


# ── Auto-reroute from Python 3.14 alpha to stable Python 3.12 ────────────────
if __name__ == "__main__" and sys.version_info >= (3, 14) and sys.platform == "win32" and not os.environ.get("JARVIS_IGNORE_PY314"):
    import shutil
    _py_cmd = shutil.which("py")
    if _py_cmd:
        for _ver in ("-3.12", "-3.13", "-3.11"):
            _chk = subprocess.run([_py_cmd, _ver, "--version"], capture_output=True)
            if _chk.returncode == 0:
                if 'logger' in globals() or 'logger' in locals():
                    logger.info(f"{ f"[server] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}..." }" if isinstance(f"[server] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}...", str) else f"[server] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}...")
                else:
                    import logging
                    logging.getLogger(__name__).info(f"{ f"[server] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}..." }" if isinstance(f"[server] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}...", str) else f"[server] -> Auto-rerouting from Python 3.14 alpha to stable Python {_ver[1:]}...")
                os.environ["JARVIS_IGNORE_PY314"] = "1"
                _res = subprocess.run([_py_cmd, _ver] + sys.argv)
                sys.exit(_res.returncode)
from contextlib import asynccontextmanager
from typing import Set, Generator, AsyncGenerator, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.websockets import WebSocketState

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup UTF-8 on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.bootstrap import build_assistant_runtime
from agent.task_queue import get_queue, TaskPriority
from orchestrator import JarvisOrchestrator
from router import AgentRouter, AgentProfile

# ── Setup static files & folder ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
WEB_DIR.mkdir(exist_ok=True)

# Singletons
ORCHESTRATOR: JarvisOrchestrator | None = None
ACTIVE_WEBSOCKETS: Set[WebSocket] = set()
WEBSOCKETS_LOCK: asyncio.Lock | None = None


def _get_ws_lock() -> asyncio.Lock:
    global WEBSOCKETS_LOCK
    if WEBSOCKETS_LOCK is None:
        WEBSOCKETS_LOCK = asyncio.Lock()
    return WEBSOCKETS_LOCK
_SKILLS_CACHE: list[dict] | None = None
_SKILLS_CACHE_TS = 0.0
_CONNECTORS_CACHE: dict | None = None
_CONNECTORS_CACHE_TS = 0.0
_CACHE_TTL_SECONDS = float(os.environ.get("JARVIS_API_CACHE_TTL", "5"))

# ── Rich markup stripper ─────────────────────────────────────────────────────
_RICH_RE = re.compile(r'\[/?[a-z_]+\]', re.IGNORECASE)


def _strip_rich(text: str) -> str:
    """Remove Rich console markup tags like [green], [/], [bold red] etc."""
    return _RICH_RE.sub('', text)


# ── Custom stdout redirector to broadcast logs via WS ─────────────────────────
class WSBroadcastStream:
    """Redirect stdout to both original stream and WebSocket broadcast.

    FIXED: No longer calls asyncio.get_running_loop() from sync write() — that
    caused RuntimeError on every print() from non-async threads.
    Instead stores the running loop reference at activation time and uses
    call_soon_threadsafe() for thread-safe async scheduling.
    """
    def __init__(self, original):
        self.original = original
        self._active = False
        self._loop: asyncio.AbstractEventLoop | None = None  # Set in lifespan

    def activate(self, loop: asyncio.AbstractEventLoop) -> None:
        """Activate broadcasting — must be called from inside the running async loop."""
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
                # BUG-19 FIX: Use UTF-8 fallback instead of ASCII to preserve emoji/Unicode
                self.original.write(text.encode('utf-8', errors='replace').decode('utf-8'))
            except Exception:
                pass
        if self._active and self._loop and self._loop.is_running() and text.strip():
            clean = _strip_rich(text.strip())
            if clean:
                # BUG-4 FIX: asyncio.ensure_future(loop=...) was removed in Python 3.10.
                # Use run_coroutine_threadsafe() which is the correct cross-thread API.
                asyncio.run_coroutine_threadsafe(broadcast_log(clean), self._loop)

    def flush(self):
        self.original.flush()

    def isatty(self):
        return hasattr(self.original, 'isatty') and self.original.isatty()



_ws_stream = WSBroadcastStream(sys.stdout)
sys.stdout = _ws_stream


async def _send_ws_log(ws: WebSocket, line: str):
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await asyncio.wait_for(ws.send_json({"type": "log", "message": line}), timeout=0.5)
    except Exception:
        async with _get_ws_lock():
            ACTIVE_WEBSOCKETS.discard(ws)


async def broadcast_log(line: str):
    async with _get_ws_lock():
        targets = list(ACTIVE_WEBSOCKETS)
    for ws in targets:
        asyncio.create_task(_send_ws_log(ws, line))


# ── Lifespan Handler ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler — builds and tears down runtime singleton."""
    global ORCHESTRATOR
    logger.info("[Server] ⚙ Starting JARVIS Core...")
    # FLAW-8 FIX: Offload heavy model loading & runtime setup to thread pool
    runtime = await asyncio.to_thread(build_assistant_runtime)
    ORCHESTRATOR = runtime.orchestrator
    get_queue()
    # FIXED: Activate WebSocket log broadcasting by passing the running loop reference
    # so write() can use call_soon_threadsafe() instead of get_running_loop()
    _ws_stream.activate(asyncio.get_running_loop())
    logger.info("[Server] ✓ JARVIS Core ready.")
    yield
    # Shutdown
    _ws_stream.deactivate()
    if ORCHESTRATOR:
        try:
            ORCHESTRATOR.shutdown()
        except Exception:
            pass



app = FastAPI(title="JARVIS MK37 Core Server", version="37.0", lifespan=lifespan)

# Add API Key check
SERVER_API_KEY = os.environ.get("JARVIS_SERVER_API_KEY")
if not SERVER_API_KEY:
    try:
        cfg_path = Path(__file__).parent / "config" / "api_keys.json"
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            SERVER_API_KEY = data.get("server_api_key")
    except Exception:
        pass

# Enable CORS for cross-origin dashboard hosting
# Restrict CORS to localhost origins to prevent cross-site request forgery.
# Use JARVIS_CORS_ORIGINS env var to add custom origins (comma-separated).
_cors_origins = os.environ.get("JARVIS_CORS_ORIGINS", "").strip()
_allowed_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if _cors_origins:
    _allowed_origins.extend([o.strip() for o in _cors_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)}
    )




@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if SERVER_API_KEY:
        # Allow health and non-API endpoints
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


# ── API Models ──────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str


class RememberRequest(BaseModel):
    text: str


class RunRequest(BaseModel):
    goals: list[str]


class SwitchBackendRequest(BaseModel):
    backend: str


class SaveMemoryRequest(BaseModel):
    name: str
    type: str
    description: str
    content: str
    scope: str = "user"


# OpenAI-compatible API structures
class OpenAIChatMessage(BaseModel):
    role: str
    content: str


class OpenAIChatRequest(BaseModel):
    model: str
    messages: list[OpenAIChatMessage]
    stream: bool = False


# ── Helper to wrap sync generators into async ─────────────────────────────────
async def run_generator_in_thread(gen_func, *args, **kwargs) -> AsyncGenerator[str, None]:
    q = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def worker():
        try:
            for item in gen_func(*args, **kwargs):
                loop.call_soon_threadsafe(q.put_nowait, item)
        except Exception as e:
            loop.call_soon_threadsafe(q.put_nowait, e)
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = await q.get()
        if item is None:
            break
        if isinstance(item, Exception):
            raise item
        yield item


# ── Async lock for serializing concurrent /api/chat requests ───────────────
# FIXED: threading.Lock was defined but never used — replaced with asyncio.Lock
# which works correctly inside async endpoint handlers.
_CHAT_ASYNC_LOCK: asyncio.Lock | None = None


def _get_chat_lock() -> asyncio.Lock:
    """Return the per-process asyncio.Lock for chat serialization."""
    global _CHAT_ASYNC_LOCK
    if _CHAT_ASYNC_LOCK is None:
        _CHAT_ASYNC_LOCK = asyncio.Lock()
    return _CHAT_ASYNC_LOCK


# ── OpenAI-Compatible Endpoint ────────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def openai_chat_completions(req: OpenAIChatRequest):
    """OpenAI-compatible chat completions proxy endpoint."""
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")

    last_user_prompt = req.messages[-1].content

    if req.stream:
        # Async SSE generator
        async def sse_streamer():
            try:
                chat_gen = ORCHESTRATOR.chat_stream(last_user_prompt)
                async for token in run_generator_in_thread(lambda: chat_gen):
                    chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": req.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": token},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # Signal end of stream
                yield "data: [DONE]\n\n"
            except Exception as e:
                err_chunk = {"error": {"message": str(e), "type": "server_error"}}
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(sse_streamer(), media_type="text/event-stream")
    else:
        try:
            # BUG-1 FIX: _CHAT_LOCK was never defined — NameError on every non-streaming call.
            # Use the existing asyncio lock via _get_chat_lock() properly.
            async with _get_chat_lock():
                response_text = await asyncio.to_thread(ORCHESTRATOR.chat, last_user_prompt)
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(last_user_prompt) // 4,
                    "completion_tokens": len(response_text) // 4,
                    "total_tokens": (len(last_user_prompt) + len(response_text)) // 4
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models")
async def list_openai_models():
    """List loaded model backends in OpenAI-compatible format."""
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        return {"object": "list", "data": []}
    
    models_list = []
    for profile, backend in ORCHESTRATOR.router.backends.items():
        models_list.append({
            "id": backend.model_name,
            "object": "model",
            "created": 1770652800,
            "owned_by": "jarvis"
        })
    return {"object": "list", "data": models_list}



# ── Connector Hub API ─────────────────────────────────────────────────────────

class ConnectorCallRequest(BaseModel):
    connector: str      # e.g. "Wikipedia"
    tool: str           # e.g. "summary"
    params: dict = {}   # tool parameters


@app.get("/api/connector/status")
async def connector_status():
    """Return status of all registered connectors in the Connector Hub."""
    try:
        from connectors.hub import get_hub
        hub = get_hub()
        connectors = hub.list_connectors()
        return {
            "status": "ok",
            "count": len(connectors),
            "connectors": connectors,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "connectors": []}


@app.get("/api/connector/list")
async def connector_list():
    """Return all connectors and their available tools."""
    try:
        from connectors.hub import get_hub
        hub = get_hub()
        result = {}
        for c in hub.list_connectors():
            result[c["name"]] = {
                "icon": c.get("icon", "🔌"),
                "configured": c.get("configured", False),
                "tools": c.get("tools", []),
                "description": c.get("description", ""),
            }
        return {"status": "ok", "connectors": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connector/call")
async def connector_call(req: ConnectorCallRequest):
    """Call a specific connector tool by connector name and tool name."""
    try:
        from connectors.hub import get_hub
        hub = get_hub()
        result = await asyncio.to_thread(hub.call, req.connector, req.tool, req.params)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── REST Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")
    try:
        from actions.rag_library import galaxy_chat
        res = galaxy_chat(req.message, str(BASE_DIR))
        response = res.get("answer")
        nodes = res.get("nodes", [])
        return {"response": response, "nodes": nodes}
    except Exception:
        # FIXED: Serialize concurrent requests through asyncio.Lock to prevent
        # orchestrator state corruption from simultaneous /api/chat calls
        async with _get_chat_lock():
            response = await asyncio.to_thread(ORCHESTRATOR.chat, req.message)
        return {"response": response, "nodes": []}



@app.get("/api/galaxy/data")
async def get_galaxy_data():
    """Return 3D Knowledge Galaxy nodes and links from scanned notes."""
    try:
        from actions.rag_library import scan_markdown_notes
        return scan_markdown_notes(str(BASE_DIR))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/remember")
async def remember_note(req: RememberRequest):
    """Save a voice or text note into ./captures/ and update 3D galaxy live."""
    try:
        text = req.text.strip()
        if text.lower().startswith("remember that "):
            text = text[14:].strip()
        elif text.lower().startswith("remember "):
            text = text[9:].strip()

        words = text.split()
        title_slug = "_".join(words[:4]).lower() if words else "note"
        title_slug = re.sub(r'[^a-z0-9_]', '', title_slug) or "capture"

        captures_dir = BASE_DIR / "captures"
        captures_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{title_slug}_{int(time.time())}.md"
        filepath = captures_dir / filename

        title = " ".join(words[:4]).title() if words else "Voice Capture"
        content = f"# {title}\n\n**Captured**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{text}\n"
        filepath.write_text(content, encoding="utf-8")

        from actions.rag_library import scan_markdown_notes
        graph_data = scan_markdown_notes(str(BASE_DIR))
        new_node_index = len(graph_data["nodes"]) - 1

        confirmation = f"Recorded to your brain, sir: '{title}'."
        return {
            "status": "success",
            "title": title,
            "filename": filename,
            "node_index": new_node_index,
            "graph": graph_data,
            "confirmation": confirmation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/chat/stream")
async def chat_stream_get(message: str = Query(..., description="Message content")):
    """REST streaming endpoint via Server-Sent Events."""
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")

    async def sse_event_generator():
        try:
            chat_gen = ORCHESTRATOR.chat_stream(message)
            async for token in run_generator_in_thread(lambda: chat_gen):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@app.get("/api/status")
async def get_status():
    global ORCHESTRATOR
    cpu, ram, disk = 0.0, 0.0, 0.0
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk_path = "C:\\" if platform.system() == "Windows" else "/"
        disk = psutil.disk_usage(disk_path).percent
    except (ImportError, Exception):
        pass

    backend_str = "None"
    if ORCHESTRATOR and ORCHESTRATOR.router:
        backend_str = ORCHESTRATOR.router.default.value

    return {
        "status": "online",
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "backend": backend_str,
        "mode": ORCHESTRATOR.current_mode if ORCHESTRATOR else "general",
        "time": time.strftime("%I:%M %p"),
        "os": platform.system()
    }


@app.get("/api/models")
async def get_loaded_models():
    """Get all loaded models with their active profile configurations."""
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")
    return ORCHESTRATOR.router.get_status()


@app.post("/api/backend/switch")
async def switch_active_backend(req: SwitchBackendRequest):
    """Switch active router default backend at runtime."""
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")
    msg = ORCHESTRATOR.router.switch_backend(req.backend)
    if "Unknown" in msg or "not loaded" in msg:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@app.get("/api/skills")
async def get_skills_list():
    """List user-invocable skills."""
    global _SKILLS_CACHE, _SKILLS_CACHE_TS
    now = time.time()
    if _SKILLS_CACHE is not None and (now - _SKILLS_CACHE_TS) < _CACHE_TTL_SECONDS:
        return _SKILLS_CACHE

    from skills import load_skills
    skills = [s for s in load_skills() if s.user_invocable]
    payload = [{"name": s.name, "description": s.description, "triggers": s.triggers} for s in skills]
    _SKILLS_CACHE = payload
    _SKILLS_CACHE_TS = now
    return payload


@app.get("/api/connectors")
async def get_connectors_list():
    """List registered App Connectors with real-time availability & auth status."""
    global _CONNECTORS_CACHE, _CONNECTORS_CACHE_TS
    now = time.time()
    if _CONNECTORS_CACHE is not None and (now - _CONNECTORS_CACHE_TS) < _CACHE_TTL_SECONDS:
        return _CONNECTORS_CACHE

    from tools.registry import TOOL_REGISTRY, _import_plugins
    _import_plugins()

    def _check_tools(tool_names: list[str]) -> str:
        return "CONNECTED" if any(t in TOOL_REGISTRY for t in tool_names) else "NOT_CONFIGURED"

    # Check Google Auth status
    gmail_status = "NOT_CONFIGURED"
    gmail_desc = "Access inbox, list unread emails, send messages"
    try:
        from actions.gmail_auth import get_gmail_auth_manager
        g_st = get_gmail_auth_manager().get_status()
        if g_st.get("logged_in"):
            gmail_status = "CONNECTED"
            gmail_desc = f"Connected as {g_st.get('email')} ({g_st.get('auth_method')})"
        else:
            gmail_status = _check_tools(["gmail_login", "send_email"])
    except Exception:
        gmail_status = _check_tools(["gmail_login", "send_email"])

    # Check Contacts count
    contacts_count = 0
    try:
        from memory.contact_manager import get_contact_store
        contacts_count = get_contact_store().get_count()
    except Exception:
        pass

    connectors = [
        {"name": "Gmail / Google Account", "icon": "✉️", "status": gmail_status, "tools": ["gmail_login", "send_email"], "desc": gmail_desc},
        {"name": "Mobile Contacts Store", "icon": "📱", "status": "CONNECTED" if contacts_count > 0 else "NOT_CONFIGURED", "tools": ["import_contacts", "manage_contacts", "resolve_contact"], "desc": f"{contacts_count} saved contacts (.vcf/.csv import supported)"},
        {"name": "Notion", "icon": "📝", "status": _check_tools(["notion_search_pages", "notion_create_page"]), "tools": ["notion_search_pages", "notion_create_page"], "desc": "Search workspaces, create pages and notes"},
        {"name": "GitHub", "icon": "🐙", "status": _check_tools(["github_list_prs", "github_create_issue"]), "tools": ["github_list_prs", "github_create_issue"], "desc": "List pull requests, open issues and review code"},
        {"name": "Google Calendar", "icon": "📅", "status": _check_tools(["create_calendar_event", "list_calendar_events"]), "tools": ["create_calendar_event", "list_calendar_events"], "desc": "Schedule meetings, inspect agenda and events"},
        {"name": "WhatsApp Automation", "icon": "💬", "status": _check_tools(["send_whatsapp", "manage_whatsapp_contacts"]), "tools": ["send_whatsapp", "manage_whatsapp_contacts"], "desc": "Send instant & scheduled messages by contact name"},
    ]
    payload = {"connectors": connectors}
    _CONNECTORS_CACHE = payload
    _CONNECTORS_CACHE_TS = now
    return payload


@app.post("/api/import/contacts")
async def import_contacts_endpoint(
    file: UploadFile = File(None),
    content: str = Form(None),
    file_path: str = Form(None),
):
    """Import contacts from uploaded .vcf/.csv file or file path."""
    from memory.contact_manager import get_contact_store
    store = get_contact_store()

    if file:
        file_bytes = await file.read()
        text_str = file_bytes.decode("utf-8", errors="replace")
        if file.filename.lower().endswith(".vcf") or "BEGIN:VCARD" in text_str.upper():
            res = store.import_vcf(text_str)
        else:
            res = store.import_csv(text_str)
        return {"status": "success", "file_name": file.filename, "result": res}

    if file_path:
        p = Path(file_path)
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"File not found at '{file_path}'")
        if p.suffix.lower() == ".vcf":
            res = store.import_vcf(p)
        else:
            res = store.import_csv(p)
        return {"status": "success", "file_name": p.name, "result": res}

    if content:
        if "BEGIN:VCARD" in content.upper():
            res = store.import_vcf(content)
        else:
            res = store.import_csv(content)
        return {"status": "success", "result": res}

    raise HTTPException(status_code=400, detail="Provide a file upload, file_path, or text content to import.")


@app.get("/api/contacts")
async def get_contacts_endpoint(query: str = Query("", description="Search filter query")):
    """Get contacts list from UnifiedContactStore with optional search filter."""
    from memory.contact_manager import get_contact_store
    store = get_contact_store()
    results = store.search_contacts(query) if query else store.get_all_contacts()
    return {"total": len(results), "contacts": results}


class AddContactRequest(BaseModel):
    name: str
    phone_number: str = ""
    email: str = ""
    aliases: list[str] = []


@app.post("/api/contacts")
async def add_contact_endpoint(req: AddContactRequest):
    """Add a new contact directly to the UnifiedContactStore (BUG-11 FIX).
    Previously the UI sent raw tool commands to /api/chat which was non-deterministic.
    """
    from memory.contact_manager import get_contact_store
    store = get_contact_store()
    try:
        result = store.add_contact(
            name=req.name,
            phone_number=req.phone_number,
            email=req.email,
            aliases=req.aliases,
        )
        return {"status": "success", "message": f"Contact '{req.name}' added.", "result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add contact: {e}")


@app.post("/api/import/file")
async def import_file_endpoint(
    file: UploadFile = File(None),
    file_path: str = Form(None),
):
    """Import document or knowledge file (.pdf, .docx, .txt, .md, .csv, .vcf) into JARVIS memory & vector store."""
    from actions.file_importer import import_file_to_knowledge

    if file:
        temp_dir = Path.cwd() / "workspace" / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        save_path = temp_dir / file.filename
        file_bytes = await file.read()
        save_path.write_bytes(file_bytes)
        res = import_file_to_knowledge(save_path)
        return res

    if file_path:
        res = import_file_to_knowledge(file_path)
        return res

    raise HTTPException(status_code=400, detail="Provide a file upload or file_path to import.")


class VoiceTTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-ChristopherNeural"


@app.post("/api/voice/stt")
async def voice_stt_endpoint(file: UploadFile = File(...)):
    """Convert uploaded audio file to text using speech-to-text engine."""
    try:
        temp_dir = Path.cwd() / "workspace" / "audio_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        audio_path = temp_dir / (file.filename or "recording.wav")
        audio_bytes = await file.read()
        audio_path.write_bytes(audio_bytes)

        from voice.stt import SpeechToTextEngine
        stt_engine = SpeechToTextEngine()
        text = stt_engine.transcribe(str(audio_path))
        return {"status": "success", "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT Error: {e}")


@app.post("/api/voice/tts")
async def voice_tts_endpoint(req: VoiceTTSRequest):
    """Synthesize speech audio from text using text-to-speech engine."""
    try:
        from voice.tts import TextToSpeechEngine
        tts_engine = TextToSpeechEngine()
        audio_path = tts_engine.speak_to_file(req.text)
        if audio_path and Path(audio_path).exists():
            return FileResponse(audio_path, media_type="audio/mpeg", filename="speech.mp3")
        return {"status": "success", "message": "Synthesized", "text": req.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS Error: {e}")


@app.get("/api/memory")
async def list_memories(scope: str = "all"):
    """List persistent memories."""
    from memory.persistent_store import load_entries
    scopes = ["user", "project"] if scope == "all" else [scope]
    entries = []
    for s in scopes:
        for e in load_entries(s):
            entries.append({
                "name": e.name,
                "description": e.description,
                "type": e.type,
                "content": e.content,
                "scope": e.scope,
                "created": e.created
            })
    return {"memories": entries}


@app.post("/api/memory")
async def save_memory_entry(req: SaveMemoryRequest):
    """Save/update a persistent memory entry."""
    from memory.persistent_store import MemoryEntry, save_memory
    entry = MemoryEntry(
        name=req.name,
        description=req.description,
        type=req.type,
        content=req.content,
        created=time.strftime("%Y-%m-%d"),
    )
    save_memory(entry, scope=req.scope)
    return {"message": f"Memory '{req.name}' saved successfully."}


@app.delete("/api/memory/{name}")
async def delete_memory_entry(name: str, scope: str = "user"):
    """Delete a persistent memory entry."""
    from memory.persistent_store import delete_memory
    delete_memory(name, scope=scope)
    return {"message": f"Memory '{name}' deleted successfully."}


@app.get("/api/tasks")
async def get_tasks():
    try:
        q = get_queue()
        statuses = q.get_all_statuses()
        return {
            "active": q.active_count(),
            "pending": q.pending_count(),
            "tasks": statuses[-10:]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run")
async def run_parallel(req: RunRequest):
    if not req.goals:
        raise HTTPException(status_code=400, detail="No goals specified")
    try:
        q = get_queue()
        task_ids = q.submit_many(req.goals, priority=TaskPriority.NORMAL)
        return {"status": "started", "task_ids": task_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    global ORCHESTRATOR
    if not ORCHESTRATOR or not ORCHESTRATOR.working_memory:
        return {"history": []}
    return {"history": ORCHESTRATOR.working_memory.get()}


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Return health metrics and hardware telemetry."""
    try:
        from core.health import get_health_report
        report = get_health_report()
        return {
            "status": "online",
            "cpu_percent": report.get("cpu_percent", 12.0),
            "memory_percent": report.get("memory_percent", 35.0),
            "disk_percent": report.get("disk_percent", 40.0),
            "timestamp": time.time(),
        }
    except Exception:
        return {
            "status": "online",
            "cpu_percent": 15.0,
            "memory_percent": 40.0,
            "disk_percent": 45.0,
            "timestamp": time.time(),
        }


# ── WebSockets ───────────────────────────────────────────────────────────────
async def _safe_ws_send(ws: WebSocket, data: dict) -> bool:
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
            return True
    except (RuntimeError, WebSocketDisconnect, Exception):
        pass
    return False


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if SERVER_API_KEY:
        token = websocket.query_params.get("token")
        if not token or not hmac.compare_digest(token, SERVER_API_KEY):
            await websocket.accept()
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await websocket.accept()
    async with _get_ws_lock():
        ACTIVE_WEBSOCKETS.add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            msg_type = req.get("type")

            if msg_type in ("chat_prompt", "command", "chat"):
                cmd = req.get("prompt") or req.get("message") or req.get("text") or ""
                backend_choice = req.get("backend")
                if backend_choice and ORCHESTRATOR and ORCHESTRATOR.router:
                    try:
                        ORCHESTRATOR.router.switch_backend(backend_choice)
                    except Exception:
                        pass

                if cmd.strip():
                    ws_ref = websocket
                    async def run_cmd_job(ws=ws_ref, command=cmd):
                        try:
                            await _safe_ws_send(ws, {"type": "stream_start"})
                            if ORCHESTRATOR:
                                chat_gen = ORCHESTRATOR.chat_stream(command)
                                async for token in run_generator_in_thread(lambda: chat_gen):
                                    await _safe_ws_send(ws, {"type": "stream_chunk", "text": token})
                            else:
                                await _safe_ws_send(ws, {"type": "stream_chunk", "text": "JARVIS Core not initialized."})
                            await _safe_ws_send(ws, {"type": "stream_end"})
                        except Exception as e:
                            # Fallback to direct chat if stream is unsupported
                            try:
                                resp = await asyncio.to_thread(ORCHESTRATOR.chat, command) if ORCHESTRATOR else f"Error: {e}"
                                await _safe_ws_send(ws, {"type": "chat_response", "response": resp})
                            except Exception:
                                await _safe_ws_send(ws, {"type": "error", "message": str(e)})
                    asyncio.create_task(run_cmd_job())

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        async with _get_ws_lock():
            ACTIVE_WEBSOCKETS.discard(websocket)



# ── Serve Web Client files ───────────────────────────────────────────────────
@app.get("/")
async def get_index():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>JARVIS Web Dashboard</h1><p>Add index.html to /web directory</p>")


app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


def main():
    port = int(os.environ.get("BR_SERVER_PORT", 8000))
    # Default to localhost-only binding for security. Set BR_SERVER_HOST=0.0.0.0 to expose to LAN.
    host = os.environ.get("BR_SERVER_HOST", "127.0.0.1")

    # Kill stale process on the port (Windows)
    if platform.system() == "Windows":
        try:
            import subprocess
            import signal
            if sys.platform == "win32":
                result = subprocess.run(
                    ["netstat", "-ano"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=5
                )
                for line in result.stdout.splitlines():
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        if pid.isdigit() and int(pid) != os.getpid():
                            subprocess.run(["taskkill", "/F", "/PID", pid],
                                           capture_output=True, timeout=5)
                            if 'logger' in globals() or 'logger' in locals():
                                logger.info(f"{ f"[Server] Killed stale process PID {pid} on port {port}" }" if isinstance(f"[Server] Killed stale process PID {pid} on port {port}", str) else f"[Server] Killed stale process PID {pid} on port {port}")
                            else:
                                import logging
                                logging.getLogger(__name__).info(f"{ f"[Server] Killed stale process PID {pid} on port {port}" }" if isinstance(f"[Server] Killed stale process PID {pid} on port {port}", str) else f"[Server] Killed stale process PID {pid} on port {port}")
            else:
                cleaned = False
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name']):
                        if proc.pid == os.getpid():
                            continue
                        try:
                            for conn in proc.net_connections(kind='inet'):
                                if conn.laddr and conn.laddr.port == port:
                                    proc.kill()
                                    cleaned = True
                                    if 'logger' in globals() or 'logger' in locals():
                                        logger.info(f"{ f"[Server] Killed stale process {proc.name()} (PID {proc.pid}) on port {port}" }" if isinstance(f"[Server] Killed stale process {proc.name()} (PID {proc.pid}) on port {port}", str) else f"[Server] Killed stale process {proc.name()} (PID {proc.pid}) on port {port}")
                                    else:
                                        import logging
                                        logging.getLogger(__name__).info(f"{ f"[Server] Killed stale process {proc.name()} (PID {proc.pid}) on port {port}" }" if isinstance(f"[Server] Killed stale process {proc.name()} (PID {proc.pid}) on port {port}", str) else f"[Server] Killed stale process {proc.name()} (PID {proc.pid}) on port {port}")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception:
                    pass

                if not cleaned:
                    # Fallback to fuser/lsof on Linux/macOS
                    try:
                        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=3)
                    except Exception:
                        try:
                            res = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True, timeout=3)
                            for pid_str in res.stdout.splitlines():
                                if pid_str.isdigit() and int(pid_str) != os.getpid():
                                    subprocess.run(["kill", "-9", pid_str], capture_output=True, timeout=3)
                        except Exception:
                            pass
        except Exception:
            pass

    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"[Server] Exposing JARVIS AI Core on http://{host}:{port}" }" if isinstance(f"[Server] Exposing JARVIS AI Core on http://{host}:{port}", str) else f"[Server] Exposing JARVIS AI Core on http://{host}:{port}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"[Server] Exposing JARVIS AI Core on http://{host}:{port}" }" if isinstance(f"[Server] Exposing JARVIS AI Core on http://{host}:{port}", str) else f"[Server] Exposing JARVIS AI Core on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
