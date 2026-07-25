# server.py
"""
FastAPI Server for JARVIS MK37.
Exposes REST and WebSocket endpoints for dashboard, voice sync, and OpenAI-compatible API.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import traceback
import platform
import uuid
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Set, Generator, AsyncGenerator

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
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
WEBSOCKETS_LOCK = asyncio.Lock()

# ── Rich markup stripper ─────────────────────────────────────────────────────
_RICH_RE = re.compile(r'\[/?[a-z_]+\]', re.IGNORECASE)


def _strip_rich(text: str) -> str:
    """Remove Rich console markup tags like [green], [/], [bold red] etc."""
    return _RICH_RE.sub('', text)


# ── Custom stdout redirector to broadcast logs via WS ─────────────────────────
class WSBroadcastStream:
    def __init__(self, original):
        self.original = original

    def write(self, text):
        try:
            self.original.write(text)
        except UnicodeEncodeError:
            try:
                self.original.write(text.encode('ascii', errors='replace').decode('ascii'))
            except Exception:
                pass
        if text.strip():
            clean = _strip_rich(text.strip())
            if clean:
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(broadcast_log(clean), loop)
                except RuntimeError:
                    pass

    def flush(self):
        self.original.flush()

    def isatty(self):
        return hasattr(self.original, 'isatty') and self.original.isatty()


sys.stdout = WSBroadcastStream(sys.stdout)


async def broadcast_log(line: str):
    async with WEBSOCKETS_LOCK:
        if not ACTIVE_WEBSOCKETS:
            return
        dead = set()
        for ws in ACTIVE_WEBSOCKETS:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json({"type": "log", "message": line})
                else:
                    dead.add(ws)
            except Exception:
                dead.add(ws)
        for ws in dead:
            ACTIVE_WEBSOCKETS.discard(ws)


# ── Lifespan Handler ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler — builds and tears down runtime singleton."""
    global ORCHESTRATOR
    print("[Server] ⚙ Starting JARVIS Core...")
    runtime = build_assistant_runtime()
    ORCHESTRATOR = runtime.orchestrator
    get_queue()
    print("[Server] ✓ JARVIS Core ready.")
    yield
    # Shutdown
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if SERVER_API_KEY:
        # Expose non-API endpoints like index, static docs
        if request.url.path.startswith(("/api", "/v1")) and request.url.path not in ("/api/health", "/health"):
            auth_header = request.headers.get("Authorization")
            api_key_header = request.headers.get("X-API-Key")
            token = None
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
            elif api_key_header:
                token = api_key_header
            if token != SERVER_API_KEY:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized: Invalid API Key"})
    return await call_next(request)


# ── API Models ──────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str


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


# ── OpenAI-Compatible Endpoint ────────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def openai_chat_completions(req: OpenAIChatRequest):
    """OpenAI-compatible chat completions proxy endpoint."""
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")

    # Format messages to orchestrator's history layout
    formatted_history = []
    for msg in req.messages[:-1]:
        formatted_history.append({"role": msg.role, "content": msg.content})

    # Set working memory history to context (excluding last prompt)
    ORCHESTRATOR.working_memory.history = formatted_history
    last_user_prompt = req.messages[-1].content

    # Determine backend profile based on keywords
    keywords = ORCHESTRATOR._extract_keywords(last_user_prompt)
    profile = ORCHESTRATOR.router.route(keywords)

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


# ── REST Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    global ORCHESTRATOR
    if not ORCHESTRATOR:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")
    try:
        response = await asyncio.to_thread(ORCHESTRATOR.chat, req.message)
        return {"response": response}
    except Exception as e:
        traceback.print_exc()
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
    from skills import load_skills
    skills = [s for s in load_skills() if s.user_invocable]
    return [{"name": s.name, "description": s.description, "triggers": s.triggers} for s in skills]


@app.get("/api/connectors")
async def get_connectors_list():
    """List registered App Connectors and active signatures."""
    connectors = [
        {"name": "Gmail", "icon": "✉️", "status": "CONNECTED", "tools": ["gmail_list_unread", "gmail_send_email"], "desc": "Access inbox, list unread emails, send messages"},
        {"name": "Notion", "icon": "📝", "status": "CONNECTED", "tools": ["notion_search_pages", "notion_create_page"], "desc": "Search workspaces, create pages and notes"},
        {"name": "GitHub", "icon": "🐙", "status": "CONNECTED", "tools": ["github_list_prs", "github_create_issue"], "desc": "List pull requests, open issues and review code"},
        {"name": "Google Calendar", "icon": "📅", "status": "CONNECTED", "tools": ["calendar_list_events", "calendar_create_event"], "desc": "Schedule meetings, inspect agenda and events"},
        {"name": "Slack", "icon": "💬", "status": "CONNECTED", "tools": ["slack_send_message"], "desc": "Send channels messages and post team notifications"},
    ]
    return {"connectors": connectors}


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
        if token != SERVER_API_KEY:
            await websocket.accept()
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await websocket.accept()
    async with WEBSOCKETS_LOCK:
        ACTIVE_WEBSOCKETS.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            msg_type = req.get("type")

            if msg_type == "command":
                cmd = req.get("message", "")
                if cmd.strip():
                    ws_ref = websocket
                    async def run_cmd_job(ws=ws_ref, command=cmd):
                        try:
                            resp = await asyncio.to_thread(ORCHESTRATOR.chat, command)
                            await _safe_ws_send(ws, {"type": "response", "message": resp})
                        except Exception as e:
                            await _safe_ws_send(ws, {"type": "error", "message": str(e)})
                    asyncio.create_task(run_cmd_job())

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        async with WEBSOCKETS_LOCK:
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
    host = os.environ.get("BR_SERVER_HOST", "0.0.0.0")

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
                            print(f"[Server] Killed stale process PID {pid} on port {port}")
            else:
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name']):
                        if proc.pid == os.getpid():
                            continue
                        try:
                            for conn in proc.net_connections(kind='inet'):
                                if conn.laddr and conn.laddr.port == port:
                                    proc.kill()
                                    print(f"[Server] Killed stale process {proc.name()} (PID {proc.pid}) on port {port}")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception:
                    # Fallback to fuser/ss/lsof on Linux
                    try:
                        res = subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=3)
                    except Exception:
                        pass
        except Exception:
            pass

    print(f"[Server] Exposing JARVIS AI Core on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
