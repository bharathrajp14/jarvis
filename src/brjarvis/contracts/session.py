# src/brjarvis/contracts/session.py — Canonical Session & Handoff Contracts for BR JARVIS
"""
Canonical Session and Handoff contracts for BR JARVIS operating runtime.
Defines SessionState, SessionTurn, SessionCheckpoint, Session, and Handoff.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionState(str, Enum):
    """Canonical Session Lifecycle States."""
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    PAUSED = "PAUSED"
    COMPACTING = "COMPACTING"
    RESUMING = "RESUMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SessionTurn(BaseModel):
    """A single interaction turn within an agent session."""
    turn_id: str = Field(default_factory=lambda: f"turn-{uuid.uuid4().hex[:8]}")
    role: str = Field(default="user", description="user, assistant, system, tool")
    content: str = ""
    timestamp: float = Field(default_factory=time.time)
    backend: str = "gemini"
    latency_ms: int = 0
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    verification_evidence: Optional[str] = None
    correlation_id: str = "sys-event"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionCheckpoint(BaseModel):
    """Point-in-time snapshot for session recovery, rollback, or resume."""
    checkpoint_id: str = Field(default_factory=lambda: f"ckpt-{uuid.uuid4().hex[:8]}")
    session_id: str
    state: SessionState = SessionState.ACTIVE
    turn_index: int = 0
    active_task_id: Optional[str] = None
    snapshot_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class Session(BaseModel):
    """Canonical First-Class Session Entity."""
    session_id: str = Field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:10]}")
    session_name: str = ""
    user_id: str = "default_user"
    agent_id: str = "jarvis-general"
    device_id: str = "pc_primary"
    modality: str = "text"
    project_id: str = "global"
    workspace_id: str = "default"
    active_task_id: Optional[str] = None
    current_state: SessionState = SessionState.NEW
    active_model: str = "gemini"
    permission_mode: str = "confirm_destructive"
    current_mode: str = "general"
    turns: List[SessionTurn] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: Optional[str] = None
    event_sequence: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Handoff(BaseModel):
    """Structured Agent/Session/Provider Handoff Packet."""
    handoff_id: str = Field(default_factory=lambda: f"hoff-{uuid.uuid4().hex[:8]}")
    session_id: str
    source_agent: str = "jarvis-general"
    target_agent: str = "jarvis-coding"
    project_id: str = "global"
    goal: str
    completed: List[str] = Field(default_factory=list)
    current_state: str = ""
    failed_attempts: List[str] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    important_files: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    status: str = "OPEN"  # OPEN, CLAIMED, COMPLETED, EXPIRED
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None
