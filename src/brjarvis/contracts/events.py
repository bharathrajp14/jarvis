# src/brjarvis/contracts/events.py — Canonical Event Contracts for BR JARVIS
"""
Canonical Event and Telemetry Envelope contracts for BR JARVIS operating runtime.
Defines AgentEvent (canonical EventEnvelope) and specialized lifecycle events.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    """The Single Canonical Event Envelope across the BR JARVIS platform."""
    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    event_type: str = Field(..., description="Dot-notated event topic taxonomy e.g. task.created, tool.executed")
    timestamp: float = Field(default_factory=time.time)
    source: str = Field(default="system", description="Component or subsystem that emitted the event")
    trace_id: str = Field(default_factory=lambda: f"tr-{uuid.uuid4().hex[:16]}", description="Distributed/OpenTelemetry trace ID")
    execution_id: str = Field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}", description="Current execution turn ID")
    task_id: str = Field(default="", description="Associated task ID if applicable")
    session_id: str = Field(default="", description="Associated session ID")
    agent_id: str = Field(default="jarvis", description="Associated agent ID")
    workspace_id: str = Field(default="default", description="Associated workspace ID")
    schema_version: str = Field(default="1.0", description="Event contract schema version")
    causation_id: Optional[str] = Field(default=None, description="Event ID that directly triggered this event")
    correlation_id: str = Field(default="sys-event", description="End-to-end conversation/request tracking ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific payload body")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# EventEnvelope is an explicit alias for AgentEvent
EventEnvelope = AgentEvent
