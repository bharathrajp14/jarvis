# events/types.py — Pydantic v2 Event Models for JARVIS MK37
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = Field(..., description="Topic taxonomy e.g. system.startup, task.created")
    timestamp: float = Field(default_factory=time.time)
    correlation_id: str = Field(default="sys-event", description="Tracing/correlation ID")
    source: str = Field(default="system", description="Event emitter component")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data body")


class SystemEvent(BaseEvent):
    """System lifecycle event (startup, shutdown, health changes).

    FIXED: topic is no longer defaulted to a misleading value — callers must
    pass the specific topic (e.g., topic='system.startup').
    """
    state: Optional[str] = None


class TaskEvent(BaseEvent):
    """Task lifecycle event (created, running, completed, failed)."""
    task_id: str
    goal: str
    status: str = "pending"


class AuditEvent(BaseEvent):
    """Security audit event for permission-controlled actions."""
    action_type: str
    target: str
    user_confirmed: bool = True


class ErrorEvent(BaseEvent):
    """System or tool error event."""
    error_message: str
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None


class VoiceEvent(BaseEvent):
    """Voice recognition event."""
    transcript: str
    confidence: float = 1.0
    speaker: str = "user"


class ToolExecutionEvent(BaseEvent):
    """Tool execution lifecycle event."""
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    success: Optional[bool] = None
    result: Optional[Any] = None
    duration_ms: Optional[float] = None


class VisionEvent(BaseEvent):
    """Screen understanding / vision event."""
    active_window: Optional[str] = None
    nodes_count: int = 0
    verification_success: Optional[bool] = None
