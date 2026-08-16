# api/routes/websocket.py — Real-time Web & Mobile WebSocket Channels
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import time
import uuid
from typing import Any, Dict, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from .auth import verify_and_consume_ws_ticket, verify_session
from ..state import (
    ACTIVE_WEBSOCKETS,
    SERVER_API_KEY,
    get_orchestrator,
    get_ws_lock,
)
from brjarvis.core.version import VERSION
from brjarvis.events.bus import get_event_bus
from brjarvis.integrations.mobile.gateway import get_device_gateway
from brjarvis.integrations.mobile.session import get_mobile_session_manager


logger = logging.getLogger("JARVIS.API.WebSocket")
router = APIRouter(tags=["WebSockets"])


async def safe_ws_send(ws: WebSocket, data: dict) -> bool:
    """Safely send a JSON payload to a WebSocket client if connected."""
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
            return True
    except (RuntimeError, WebSocketDisconnect, Exception):
        pass
    return False


def _check_ws_auth(websocket: WebSocket) -> bool:
    """Validate WebSocket handshake credentials against server security policy."""
    if not SERVER_API_KEY:
        return True

    ticket = websocket.query_params.get("ticket")
    token = websocket.query_params.get("token") or websocket.query_params.get("key")

    # Check one-time ticket
    if ticket and verify_and_consume_ws_ticket(ticket):
        return True

    # Check direct API key match
    if token and hmac.compare_digest(token, SERVER_API_KEY):
        return True

    # Check session token
    if token and verify_session(token):
        return True

    # Check session cookie
    cookies = websocket.cookies
    if cookies and "jarvis_session" in cookies:
        if verify_session(cookies["jarvis_session"]):
            return True

    return False


@router.websocket("/ws")
@router.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time bidirectional WebSocket for Web Dashboard chat, telemetry, and event bus.
    Supports short-lived connection tickets, session tokens, and ping/pong heartbeats.
    """
    from .chat import run_generator_in_thread

    if not _check_ws_auth(websocket):
        # Reject BEFORE accept so the server never logs "connection open"
        # and the client gets code 4001 immediately, stopping the reconnect loop.
        await websocket.close(code=4001, reason="Unauthorized: Invalid WebSocket Ticket or Session")
        return

    await websocket.accept()
    async with get_ws_lock():
        ACTIVE_WEBSOCKETS.add(websocket)

    # Send initial ServerReady message
    await safe_ws_send(websocket, {
        "event_id": str(uuid.uuid4()),
        "type": "ServerReady",
        "timestamp": time.time(),
        "payload": {
            "status": "ONLINE",
            "server_version": VERSION,
        }
    })

    try:
        while True:
            raw_data = await websocket.receive_text()
            if not raw_data.strip():
                continue

            try:
                req = json.loads(raw_data)
            except json.JSONDecodeError:
                await safe_ws_send(websocket, {
                    "event_id": str(uuid.uuid4()),
                    "type": "ErrorMessage",
                    "timestamp": time.time(),
                    "payload": {"error": "Invalid JSON format"},
                })
                continue

            msg_type = req.get("type", "").lower()
            request_id = req.get("request_id") or str(uuid.uuid4())

            # 1. Heartbeat Ping / Pong
            if msg_type in ("ping", "heartbeat"):
                await safe_ws_send(websocket, {
                    "event_id": str(uuid.uuid4()),
                    "type": "Heartbeat",
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "payload": {"status": "pong"},
                })
                continue

            # 2. Chat / Command execution
            if msg_type in ("chat_prompt", "command", "chat", "clientcommand"):
                cmd = (
                    req.get("prompt")
                    or req.get("message")
                    or req.get("text")
                    or (req.get("payload") or {}).get("command")
                    or ""
                )
                backend_choice = req.get("backend") or (req.get("payload") or {}).get("backend")
                task_id = req.get("task_id") or f"task_{uuid.uuid4().hex[:8]}"

                orch = get_orchestrator()
                if backend_choice and orch and getattr(orch, "router", None):
                    try:
                        orch.router.switch_backend(backend_choice)
                    except Exception:
                        pass

                if cmd.strip():
                    ws_ref = websocket
                    async def run_cmd_job(ws=ws_ref, command=cmd, tid=task_id, rid=request_id):
                        try:
                            # Stream start / TaskCreated
                            await safe_ws_send(ws, {
                                "event_id": str(uuid.uuid4()),
                                "type": "TaskCreated",
                                "request_id": rid,
                                "task_id": tid,
                                "timestamp": time.time(),
                                "payload": {"goal": command, "status": "running"},
                            })
                            await safe_ws_send(ws, {
                                "event_id": str(uuid.uuid4()),
                                "type": "stream_start",
                                "request_id": rid,
                                "task_id": tid,
                                "timestamp": time.time(),
                            })

                            active_orch = get_orchestrator()
                            full_text = ""
                            if active_orch:
                                chat_gen = active_orch.chat_stream(command)
                                async for token_str in run_generator_in_thread(lambda: chat_gen):
                                    full_text += token_str
                                    await safe_ws_send(ws, {
                                        "event_id": str(uuid.uuid4()),
                                        "type": "stream_chunk",
                                        "request_id": rid,
                                        "task_id": tid,
                                        "text": token_str,
                                        "payload": {"chunk": token_str},
                                    })
                            else:
                                msg = "JARVIS Core not initialized."
                                full_text = msg
                                await safe_ws_send(ws, {
                                    "event_id": str(uuid.uuid4()),
                                    "type": "stream_chunk",
                                    "request_id": rid,
                                    "task_id": tid,
                                    "text": msg,
                                    "payload": {"chunk": msg},
                                })

                            await safe_ws_send(ws, {
                                "event_id": str(uuid.uuid4()),
                                "type": "stream_end",
                                "request_id": rid,
                                "task_id": tid,
                                "timestamp": time.time(),
                            })
                            await safe_ws_send(ws, {
                                "event_id": str(uuid.uuid4()),
                                "type": "TaskUpdated",
                                "request_id": rid,
                                "task_id": tid,
                                "timestamp": time.time(),
                                "payload": {"status": "completed", "result": full_text},
                            })
                        except Exception as e:
                            logger.exception("Error executing WebSocket command: %s", e)
                            await safe_ws_send(ws, {
                                "event_id": str(uuid.uuid4()),
                                "type": "ErrorMessage",
                                "request_id": rid,
                                "task_id": tid,
                                "timestamp": time.time(),
                                "payload": {"error": str(e)},
                            })

                    asyncio.create_task(run_cmd_job())

            # 3. Status Query
            elif msg_type == "status_query":
                orch = get_orchestrator()
                mode = getattr(orch, "current_mode", "general") if orch else "offline"
                await safe_ws_send(websocket, {
                    "event_id": str(uuid.uuid4()),
                    "type": "SystemMessage",
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "payload": {
                        "status": "ONLINE",
                        "mode": mode,
                        "active_clients": len(ACTIVE_WEBSOCKETS),
                    },
                })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WebSocket connection terminated: %s", exc)
    finally:
        async with get_ws_lock():
            ACTIVE_WEBSOCKETS.discard(websocket)


@router.websocket("/mobile/ws")
@router.websocket("/api/v1/mobile/ws")
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
