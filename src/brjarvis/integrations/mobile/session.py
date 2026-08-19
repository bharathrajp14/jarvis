# mobile/session.py — Android Companion Secure Session & Dispatcher
"""
Manages live WebSocket sessions with paired Android companion devices.
Handles request/response correlation, command dispatching, and heartbeat monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .protocol import MobileMessage, MobileMessageType

logger = logging.getLogger("JARVIS.MobileSession")


class MobileDeviceSession:
    """Represents an active WebSocket connection to a paired Android device."""

    def __init__(self, device_id: str, ws: Any):
        self.device_id = device_id
        self.ws = ws
        self.last_heartbeat = time.time()
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def send_message(self, msg: MobileMessage) -> None:
        raw_json = msg.to_json()
        await self.ws.send_text(raw_json)

    async def request(
        self, msg_type: MobileMessageType, payload: Dict[str, Any], timeout: float = 15.0
    ) -> Dict[str, Any]:
        """Send a request message and await correlated response by msg_id."""
        msg_id = str(uuid.uuid4())
        msg = MobileMessage(
            msg_type=msg_type, msg_id=msg_id, device_id=self.device_id, payload=payload, timestamp=time.time()
        )
        fut = asyncio.get_running_loop().create_future()
        self._pending_requests[msg_id] = fut

        try:
            await self.send_message(msg)
            result = await asyncio.wait_for(fut, timeout=timeout)
            return result
        finally:
            self._pending_requests.pop(msg_id, None)

    def handle_incoming_message(self, msg_json: str) -> None:
        """Handle incoming message from the device WebSocket."""
        try:
            msg = MobileMessage.from_json(msg_json)
            self.last_heartbeat = time.time()

            if msg.msg_type in (MobileMessageType.HEARTBEAT, MobileMessageType.HEARTBEAT_ACK):
                return

            # Check if this resolves a pending future
            if msg.msg_id in self._pending_requests:
                fut = self._pending_requests[msg.msg_id]
                if not fut.done():
                    fut.set_result(msg.payload)
                return

            logger.info("Received mobile event [%s] from %s: %s", msg.msg_type.value, self.device_id, msg.payload)

        except Exception as e:
            logger.error("Error processing incoming mobile message from %s: %s", self.device_id, e)


class MobileSessionManager:
    """Manages pool of active mobile device sessions with keepalive heartbeat watchdog."""

    def __init__(self):
        self._sessions: Dict[str, MobileDeviceSession] = {}
        self._lock = asyncio.Lock()
        self._watchdog_task: Optional[asyncio.Task] = None

    async def register_session(self, device_id: str, ws: Any) -> MobileDeviceSession:
        async with self._lock:
            session = MobileDeviceSession(device_id, ws)
            self._sessions[device_id] = session
            logger.info("Mobile session registered for device %s", device_id)
            if self._watchdog_task is None or self._watchdog_task.done():
                self._watchdog_task = asyncio.create_task(self._keepalive_loop())
            return session

    async def remove_session(self, device_id: str) -> None:
        async with self._lock:
            self._sessions.pop(device_id, None)
            logger.info("Mobile session removed for device %s", device_id)

    def get_session(self, device_id: str) -> Optional[MobileDeviceSession]:
        return self._sessions.get(device_id)

    def get_any_active_device_id(self) -> Optional[str]:
        return next(iter(self._sessions.keys()), None) if self._sessions else None

    def list_active_devices(self) -> List[str]:
        return list(self._sessions.keys())

    async def _keepalive_loop(self, interval: float = 15.0) -> None:
        """Periodic background ping loop ensuring responsive mobile channels."""
        while True:
            await asyncio.sleep(interval)
            async with self._lock:
                if not self._sessions:
                    break
                now = time.time()
                dead = []
                for did, session in self._sessions.items():
                    if (now - session.last_heartbeat) > 40.0:
                        dead.append(did)
                    else:
                        try:
                            msg = MobileMessage(
                                msg_type=MobileMessageType.HEARTBEAT,
                                msg_id=str(uuid.uuid4()),
                                device_id=did,
                                payload={},
                                timestamp=now,
                            )
                            asyncio.create_task(session.send_message(msg))
                        except Exception:
                            dead.append(did)

                for did in dead:
                    self._sessions.pop(did, None)
                    logger.warning("Mobile device %s timed out. Session pruned.", did)


_session_manager_instance: Optional[MobileSessionManager] = None


def get_mobile_session_manager() -> MobileSessionManager:
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = MobileSessionManager()
    return _session_manager_instance
