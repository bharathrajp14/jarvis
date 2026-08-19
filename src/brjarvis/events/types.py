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
    trace_id: str = Field(default_factory=lambda: f"tr-{uuid.uuid4().hex[:16]}", description="Distributed trace ID")
    execution_id: str = Field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}", description="Execution turn ID")
    agent_id: str = Field(default="jarvis", description="Agent ID emitting event")
    workspace_id: str = Field(default="default", description="Workspace ID context")
    schema_version: str = Field(default="1.0", description="Contract schema version")
    causation_id: Optional[str] = Field(default=None, description="Triggering event ID")
    source: str = Field(default="system", description="Event emitter component")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data body")

    @property
    def event_type(self) -> str:
        """Alias for topic for contract compatibility."""
        return self.topic


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


class AgentLifecycleEvent(BaseEvent):
    """Agent thinking and loop lifecycle event."""
    session_id: str = ""
    task_id: str = ""
    phase: str = "thinking"  # started, thinking, context_started, context_completed, plan_created, plan_updated, interrupted, cancelled, completed
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class PermissionEvent(BaseEvent):
    """Permission request and resolution lifecycle event."""
    request_id: str = ""
    session_id: str = ""
    task_id: str = ""
    tool_name: str = ""
    action: str = ""
    target: str = ""
    risk_level: str = "low"
    decision: str = "pending"  # requested, granted, denied, cancelled
    reason: str = ""


class ToolLifecycleEvent(BaseEvent):
    """Detailed tool execution lifecycle event."""
    tool_name: str
    session_id: str = ""
    task_id: str = ""
    step_id: str = ""
    status: str = "requested"  # requested, started, progress, completed, failed
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    verified: bool = False
    verification_notes: str = ""


class VerificationEvent(BaseEvent):
    """Physical state verification lifecycle event."""
    session_id: str = ""
    task_id: str = ""
    tool_name: str = ""
    target: str = ""
    verified: bool = False
    status: str = "started"  # started, completed, failed
    evidence: str = ""
    error: Optional[str] = None


class ArtifactLifecycleEvent(BaseEvent):
    """User-facing artifact lifecycle event."""
    artifact_id: str
    session_id: str = ""
    task_id: str = ""
    path: str = ""
    filename: str = ""
    mime_type: str = "text/plain"
    status: str = "created"  # created, validating, ready, opening, verified, failed
    verified: bool = False
    error: Optional[str] = None


class SessionLifecycleEvent(BaseEvent):
    """Agent session lifecycle event."""
    session_id: str
    action: str = "started"  # started, resumed, updated, closed
    mode: str = "general"
    active_model: str = "gemini"
    turns_count: int = 0

