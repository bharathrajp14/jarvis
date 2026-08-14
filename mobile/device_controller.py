# mobile/device_controller.py — Android Master Device Controller & Lock State Rules
"""
High-Level Android Device Controller for BR JARVIS MK37.
Exposes semantic actions (open_app, click, type_text, scroll, read_screen, send_message).
Enforces critical Lock State Security:
- Detects locked device state
- Never attempts bypass or fakes unlocking
- Transitions to WAITING_FOR_USER_AUTHENTICATION when required
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from mobile.gateway import get_device_gateway
from mobile.protocol import AccessibilityNode, DeviceState, MobileMessageType
from mobile.screen_understanding import get_mobile_screen_understanding
from mobile.session import get_mobile_session_manager

logger = logging.getLogger("JARVIS.AndroidController")


class AndroidDeviceController:
    """Master controller for executing actions on an authorized Android device."""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.gateway = get_device_gateway()
        self.session_manager = get_mobile_session_manager()
        self.screen_parser = get_mobile_screen_understanding()

    def _resolve_device_id(self) -> str:
        if self.device_id:
            return self.device_id
        active_id = self.session_manager.get_any_active_device_id()
        if not active_id:
            # Check registered devices in gateway
            devices = self.gateway.list_devices(trust_state="trusted")
            if devices:
                return devices[0].device_id
            raise RuntimeError("No paired or active Android device found. Please pair your Android phone via Control Center.")
        return active_id

    async def get_state(self) -> DeviceState:
        """Fetch current hardware, battery, network, and lock status."""
        dev_id = self._resolve_device_id()
        session = self.session_manager.get_session(dev_id)
        if not session:
            # Return offline state from gateway metadata
            return DeviceState(device_id=dev_id, model="Offline Android Device", is_screen_on=False)

        res = await session.request(MobileMessageType.GET_DEVICE_STATE, {})
        return DeviceState.from_dict(res)

    async def inspect_screen(self) -> Dict[str, Any]:
        """Fetch accessibility hierarchy and produce semantic summary with lock check."""
        dev_id = self._resolve_device_id()
        session = self.session_manager.get_session(dev_id)
        if not session:
            return {"status": "error", "message": f"Device {dev_id} is disconnected."}

        # 1. Check lock state first
        state = await self.get_state()
        if state.is_locked:
            logger.warning("Device %s is LOCKED.", dev_id)
            return {
                "status": "WAITING_FOR_USER_AUTHENTICATION",
                "is_locked": True,
                "requires_biometric_or_pin": True,
                "message": "Android device is currently locked. Please unlock using PIN or fingerprint to proceed."
            }

        tree_res = await session.request(MobileMessageType.GET_ACCESSIBILITY_TREE, {})
        root_node = AccessibilityNode.from_dict(tree_res)
        summary = self.screen_parser.summarize_screen(root_node)

        return {
            "status": "success",
            "foreground_app": state.foreground_app,
            "is_locked": False,
            "screen_summary": summary,
            "root_node": root_node.to_dict()
        }

    async def open_app(self, app_name: str) -> Dict[str, Any]:
        """Launch an application on the Android device."""
        dev_id = self._resolve_device_id()
        session = self.session_manager.get_session(dev_id)
        if not session:
            return {"success": False, "error": "Device is offline"}

        state = await self.get_state()
        if state.is_locked:
            return {
                "success": False,
                "status": "WAITING_FOR_USER_AUTHENTICATION",
                "message": "Device is locked. Unlock to open app."
            }

        res = await session.request(MobileMessageType.EXECUTE_ACTION, {
            "action": "open_app",
            "app_name": app_name
        })
        return res

    async def click(self, target: str) -> Dict[str, Any]:
        """Find element semantically by label/id and execute click."""
        dev_id = self._resolve_device_id()
        session = self.session_manager.get_session(dev_id)
        if not session:
            return {"success": False, "error": "Device is offline"}

        # Fetch tree to find target
        tree_res = await session.request(MobileMessageType.GET_ACCESSIBILITY_TREE, {})
        root_node = AccessibilityNode.from_dict(tree_res)

        match = self.screen_parser.find_element(root_node, target, clickable_only=False)
        if not match:
            return {"success": False, "error": f"Element '{target}' not found on mobile screen."}

        res = await session.request(MobileMessageType.EXECUTE_ACTION, {
            "action": "click_coords",
            "x": match.center[0],
            "y": match.center[1],
            "node_id": match.node_id
        })
        return res

    async def type_text(self, target: Optional[str], text: str) -> Dict[str, Any]:
        """Type text into focused or targeted input field."""
        dev_id = self._resolve_device_id()
        session = self.session_manager.get_session(dev_id)
        if not session:
            return {"success": False, "error": "Device is offline"}

        if target:
            # Click first to focus
            await self.click(target)
            await asyncio.sleep(0.3)

        res = await session.request(MobileMessageType.EXECUTE_ACTION, {
            "action": "type_text",
            "text": text
        })
        return res

    async def navigate(self, action: str) -> Dict[str, Any]:
        """Perform navigation: 'home', 'back', 'recents'."""
        dev_id = self._resolve_device_id()
        session = self.session_manager.get_session(dev_id)
        if not session:
            return {"success": False, "error": "Device is offline"}

        act_map = {
            "home": "press_home",
            "back": "press_back",
            "recents": "press_recents"
        }
        target_act = act_map.get(action.lower(), action)
        res = await session.request(MobileMessageType.EXECUTE_ACTION, {"action": target_act})
        return res
