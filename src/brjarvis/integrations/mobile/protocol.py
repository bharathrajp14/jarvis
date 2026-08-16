# mobile/protocol.py — Universal Mobile Task & Communication Protocol
"""
Protocol specification for secure Android Companion communication over TLS/WebSocket.
Defines message schemas, accessibility tree models, and device state payloads.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MobileMessageType(str, Enum):
    # Pairing & Auth
    HANDSHAKE_REQUEST = "handshake_request"
    HANDSHAKE_RESPONSE = "handshake_response"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"

    # Device State
    GET_DEVICE_STATE = "get_device_state"
    DEVICE_STATE_RESPONSE = "device_state_response"

    # Accessibility & UI
    GET_ACCESSIBILITY_TREE = "get_accessibility_tree"
    ACCESSIBILITY_TREE_RESPONSE = "accessibility_tree_response"

    # Actions
    EXECUTE_ACTION = "execute_action"
    ACTION_RESULT = "action_result"

    # Screen Streaming & Media
    START_SCREEN_STREAM = "start_screen_stream"
    STOP_SCREEN_STREAM = "stop_screen_stream"
    SCREEN_FRAME = "screen_frame"
    TAKE_SCREENSHOT = "take_screenshot"
    SCREENSHOT_RESPONSE = "screenshot_response"

    # Events & Alerts
    NOTIFICATION_EVENT = "notification_event"
    LOCK_STATE_EVENT = "lock_state_event"
    ERROR_EVENT = "error_event"


@dataclass
class AccessibilityNode:
    node_id: int
    class_name: str
    package_name: str
    text: str = ""
    content_description: str = ""
    view_id: str = ""
    bounds: List[int] = field(default_factory=lambda: [0, 0, 0, 0])  # [left, top, right, bottom]
    is_clickable: bool = False
    is_editable: bool = False
    is_focusable: bool = False
    is_scrollable: bool = False
    is_visible_to_user: bool = True
    children: List[AccessibilityNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["children"] = [c.to_dict() if isinstance(c, AccessibilityNode) else c for c in self.children]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AccessibilityNode:
        raw = dict(data)
        if "children" in raw and isinstance(raw["children"], list):
            raw["children"] = [AccessibilityNode.from_dict(c) if isinstance(c, dict) else c for c in raw["children"]]
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


@dataclass
class DeviceState:
    device_id: str
    model: str = "Android Device"
    battery_level: int = 100
    is_charging: bool = False
    network_type: str = "WIFI"  # WIFI, CELLULAR, NONE
    wifi_ssid: str = ""
    foreground_app: str = "com.android.launcher"
    is_screen_on: bool = True
    is_locked: bool = False
    requires_biometric_or_pin: bool = False
    screen_width: int = 1080
    screen_height: int = 2400
    installed_apps: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeviceState:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MobileMessage:
    msg_type: MobileMessageType
    msg_id: str
    device_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        return json.dumps(d)

    @classmethod
    def from_json(cls, json_str: str) -> MobileMessage:
        data = json.loads(json_str)
        return cls(
            msg_type=MobileMessageType(data["msg_type"]),
            msg_id=data.get("msg_id", ""),
            device_id=data.get("device_id", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time())
        )
