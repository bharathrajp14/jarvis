# api/routes/websocket.py — Real-time Web & Mobile WebSocket Channels
from __future__ import annotations

import asyncio
import hmac
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from api.routes.auth import verify_and_consume_ws_ticket
from api.state import (
    ACTIVE_WEBSOCKETS,
    SERVER_API_KEY,
    get_orchestrator,
    get_ws_lock,
)
from mobile.gateway import get_device_gateway
from mobile.session import get_mobile_session_manager

logger = logging.getLogger("JARVIS.API.WebSocket")
router = APIRouter(tags=["WebSockets"])


async def safe_ws_send(ws: WebSocket, data: dict) -> bool:
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
            return True
    except (RuntimeError, WebSocketDisconnect, Exception):
        pass
    return False


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time bidirectional WebSocket for Web Dashboard chat & stdout logs.
    Supports short-lived connection tickets and API keys.
    """
    from api.routes.chat import run_generator_in_thread
    orchestrator = get_orchestrator()

    if SERVER_API_KEY:
        ticket = websocket.query_params.get("ticket")
        token = websocket.query_params.get("token")
        authorized = False

        if ticket and verify_and_consume_ws_ticket(ticket):
            authorized = True
        elif token and hmac.compare_digest(token, SERVER_API_KEY):
            authorized = True

        if not authorized:
            await websocket.accept()
            await websocket.close(code=4001, reason="Unauthorized: Invalid WebSocket Ticket or Key")
            return

    await websocket.accept()
    async with get_ws_lock():
        ACTIVE_WEBSOCKETS.add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            req = json.loads(data)
            msg_type = req.get("type")

            if msg_type in ("chat_prompt", "command", "chat"):
                cmd = req.get("prompt") or req.get("message") or req.get("text") or ""
                backend_choice = req.get("backend")
                orch = get_orchestrator()
                if backend_choice and orch and getattr(orch, "router", None):
                    try:
                        orch.router.switch_backend(backend_choice)
                    except Exception:
                        pass

                if cmd.strip():
                    ws_ref = websocket
                    async def run_cmd_job(ws=ws_ref, command=cmd):
                        try:
                            await safe_ws_send(ws, {"type": "stream_start"})
                            active_orch = get_orchestrator()
                            if active_orch:
                                chat_gen = active_orch.chat_stream(command)
                                async for token_str in run_generator_in_thread(lambda: chat_gen):
                                    await safe_ws_send(ws, {"type": "stream_chunk", "text": token_str})
                            else:
                                await safe_ws_send(ws, {"type": "stream_chunk", "text": "JARVIS Core not initialized."})
                            await safe_ws_send(ws, {"type": "stream_end"})
                        except Exception as e:
                            try:
                                active_orch = get_orchestrator()
                                resp = await asyncio.to_thread(active_orch.chat, command) if active_orch else f"Error: {e}"
                                await safe_ws_send(ws, {"type": "chat_response", "response": resp})
                            except Exception:
                                await safe_ws_send(ws, {"type": "error", "message": str(e)})
                    asyncio.create_task(run_cmd_job())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WebSocket connection closed: %s", exc)
    finally:
        async with get_ws_lock():
            ACTIVE_WEBSOCKETS.discard(websocket)


@router.websocket("/mobile/ws")
async def mobile_websocket_endpoint(websocket: WebSocket):
    """Secure WebSocket endpoint for Mobile Companion app with authentication & keepalive."""
    gateway = get_device_gateway()
    session_mgr = get_mobile_session_manager()

    device_id = websocket.query_params.get("device_id")
    token = websocket.query_params.get("token")

    if not device_id or not token or not gateway.verify_auth_token(device_id, token):
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized Mobile Device")
        return

    await websocket.accept()
    session = await session_mgr.register_session(device_id, websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            session.handle_incoming_message(raw_text)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Mobile WS exception for %s: %s", device_id, e)
    finally:
        await session_mgr.remove_session(device_id)
