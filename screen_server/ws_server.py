# screen_server/ws_server.py — Asyncio WebSocket Server for JARVIS MK37 Screen Sharing
from __future__ import annotations

import logging
import asyncio
import json
import os
import threading
from typing import Any, Set

try:
    import websockets
    from websockets.server import serve as ws_serve
    _ws_available = True
except ImportError:
    _ws_available = False

logger = logging.getLogger(__name__)


class ScreenShareServer:
    """Manages WebSocket connections and frame broadcasting."""

    def __init__(self, port: int = 8765, token: str | None = None, ssl_context: Any | None = None):
        self.port = port
        self.token = token
        self.ssl_context = ssl_context
        self.host = os.environ.get("SCREEN_SHARE_HOST", "127.0.0.1")
        self.meta: dict = {"type": "meta", "width": 1920, "height": 1080, "fps": 10}
        self._viewers: Set[Any] = set()
        self._viewers_lock = threading.Lock()
        self._server: Any = None

    def update_meta(self, width: int, height: int, fps: int = 10) -> None:
        """Update stream resolution and frame rate metadata."""
        self.meta.update({"width": width, "height": height, "fps": fps})

    @property
    def viewer_count(self) -> int:
        with self._viewers_lock:
            return len(self._viewers)

    async def _handler(self, websocket: Any) -> None:
        """Handle a single viewer connection."""
        # Token authentication
        if self.token:
            try:
                auth_header = ""
                if hasattr(websocket, "request") and hasattr(websocket.request, "headers"):
                    auth_header = websocket.request.headers.get("Authorization", "")
                elif hasattr(websocket, "request_headers"):
                    auth_header = websocket.request_headers.get("Authorization", "")

                if auth_header != f"Bearer {self.token}":
                    try:
                        first_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        if isinstance(first_msg, str):
                            auth_data = json.loads(first_msg)
                            if auth_data.get("token") != self.token:
                                await websocket.close(1008, "Unauthorized")
                                return
                    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
                        await websocket.close(1008, "Unauthorized")
                        return
            except Exception:
                await websocket.close(1008, "Auth error")
                return

        # Send meta message
        try:
            await websocket.send(json.dumps(self.meta))
        except Exception:
            return

        # Register viewer
        with self._viewers_lock:
            self._viewers.add(websocket)

        try:
            async for _ in websocket:
                pass  # Keep connection open until client disconnects
        except Exception:
            pass
        finally:
            with self._viewers_lock:
                self._viewers.discard(websocket)

    async def start(self) -> None:
        """Start the WebSocket server (non-blocking)."""
        if not _ws_available:
            raise RuntimeError("websockets library not installed. Run: pip install websockets")

        kwargs = {}
        if self.ssl_context:
            kwargs["ssl"] = self.ssl_context

        self._server = await ws_serve(
            self._handler,
            self.host,
            self.port,
            **kwargs
        )
        protocol = "wss" if self.ssl_context else "ws"
        logger.info(f"[ScreenShare] WebSocket server listening on {protocol}://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server and disconnect all viewers."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        with self._viewers_lock:
            viewers_copy = set(self._viewers)
            self._viewers.clear()

        for ws in viewers_copy:
            try:
                await ws.close(1001, "Server shutting down")
            except Exception:
                pass

        logger.info("[ScreenShare] WebSocket server stopped")

    async def broadcast(self, frame_data: bytes) -> None:
        """Send a JPEG frame to all connected viewers."""
        with self._viewers_lock:
            viewers_copy = set(self._viewers)

        if not viewers_copy:
            return

        async def _send_to_viewer(ws):
            try:
                await asyncio.wait_for(ws.send(frame_data), timeout=2.0)
                return None
            except Exception:
                return ws
                
        results = await asyncio.gather(*[_send_to_viewer(ws) for ws in viewers_copy])
        disconnected = [ws for ws in results if ws is not None]

        if disconnected:
            with self._viewers_lock:
                for ws in disconnected:
                    self._viewers.discard(ws)
