# api/routes/chat.py — Chat, Streaming, Model Switching & OpenAI Proxy Endpoints
from __future__ import annotations

import json
import time
import uuid
import asyncio
import logging
import threading
from pathlib import Path
from typing import List, AsyncGenerator, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.state import get_orchestrator

logger = logging.getLogger("JARVIS.API.Chat")
router = APIRouter(tags=["Chat"])

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_CHAT_ASYNC_LOCK: asyncio.Lock | None = None


def _get_chat_lock() -> asyncio.Lock:
    global _CHAT_ASYNC_LOCK
    if _CHAT_ASYNC_LOCK is None:
        _CHAT_ASYNC_LOCK = asyncio.Lock()
    return _CHAT_ASYNC_LOCK


class ChatRequest(BaseModel):
    message: str


class SwitchBackendRequest(BaseModel):
    backend: str


class OpenAIChatMessage(BaseModel):
    role: str
    content: str


class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIChatMessage]
    stream: bool = False


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


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """Main conversational endpoint."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")
    try:
        from actions.rag_library import galaxy_chat
        res = galaxy_chat(req.message, str(_BASE_DIR))
        response = res.get("answer")
        nodes = res.get("nodes", [])
        return {"response": response, "nodes": nodes}
    except Exception:
        async with _get_chat_lock():
            response = await asyncio.to_thread(orchestrator.chat, req.message)
        return {"response": response, "nodes": []}


@router.get("/api/chat/stream")
async def chat_stream_get(message: str = Query(..., description="Message content")):
    """REST streaming endpoint via Server-Sent Events."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")

    async def sse_event_generator():
        try:
            chat_gen = orchestrator.chat_stream(message)
            async for token in run_generator_in_thread(lambda: chat_gen):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@router.post("/v1/chat/completions")
async def openai_chat_completions(req: OpenAIChatRequest):
    """OpenAI-compatible chat completions proxy endpoint."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")

    last_user_prompt = req.messages[-1].content

    if req.stream:
        async def sse_streamer():
            try:
                chat_gen = orchestrator.chat_stream(last_user_prompt)
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
                yield "data: [DONE]\n\n"
            except Exception as e:
                err_chunk = {"error": {"message": str(e), "type": "server_error"}}
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(sse_streamer(), media_type="text/event-stream")
    else:
        try:
            async with _get_chat_lock():
                response_text = await asyncio.to_thread(orchestrator.chat, last_user_prompt)
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


@router.get("/v1/models")
async def list_openai_models():
    """List loaded model backends in OpenAI-compatible format."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        return {"object": "list", "data": []}

    models_list = []
    for profile, backend in orchestrator.router.backends.items():
        models_list.append({
            "id": backend.model_name,
            "object": "model",
            "created": 1770652800,
            "owned_by": "jarvis"
        })
    return {"object": "list", "data": models_list}


@router.get("/api/models")
async def get_loaded_models():
    """Get all loaded models with their active profile configurations."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")
    return orchestrator.router.get_status()


@router.post("/api/backend/switch")
async def switch_active_backend(req: SwitchBackendRequest):
    """Switch active router default backend at runtime."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="JARVIS not initialized")
    msg = orchestrator.router.switch_backend(req.backend)
    if "Unknown" in msg or "not loaded" in msg:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@router.get("/api/history")
async def get_history():
    """Retrieve working conversation memory history."""
    orchestrator = get_orchestrator()
    if not orchestrator or not orchestrator.working_memory:
        return {"history": []}
    return {"history": orchestrator.working_memory.get()}
