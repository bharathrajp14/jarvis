# computer/types.py — Pydantic v2 Data Models for Computer Operator Subsystem
from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ActionType(str, enum.Enum):
    MOUSE_MOVE = "MOUSE_MOVE"
    MOUSE_CLICK = "MOUSE_CLICK"
    DOUBLE_CLICK = "DOUBLE_CLICK"
    RIGHT_CLICK = "RIGHT_CLICK"
    MOUSE_SCROLL = "MOUSE_SCROLL"
    DRAG_AND_DROP = "DRAG_AND_DROP"
    KEYBOARD_TYPE = "KEYBOARD_TYPE"
    KEYBOARD_PRESS = "KEYBOARD_PRESS"
    HOTKEY = "HOTKEY"
    CLIPBOARD_SET = "CLIPBOARD_SET"
    CLIPBOARD_GET = "CLIPBOARD_GET"
    APP_FOCUS = "APP_FOCUS"
    WINDOW_FOCUS = "WINDOW_FOCUS"
    TAKE_SCREENSHOT = "TAKE_SCREENSHOT"


class ComputerAction(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType
    x: Optional[int] = None
    y: Optional[int] = None
    target_x: Optional[int] = None
    target_y: Optional[int] = None
    scroll_clicks: int = 0
    text: Optional[str] = None
    keys: List[str] = Field(default_factory=list)
    description: str = ""
    requires_approval: bool = False


class ActionResult(BaseModel):
    action_id: str
    success: bool
    verification_message: str = "Execution Verified"
    data: Optional[Any] = None
    timestamp: float = Field(default_factory=time.time)
