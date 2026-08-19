# src/brjarvis/contracts/workflow.py — Canonical Workflow Contracts for BR JARVIS
"""
Canonical Workflow contracts for BR JARVIS operating runtime.
Defines WorkflowStatus, WorkflowCheckpoint, and WorkflowState.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Canonical Workflow Execution Statuses."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAUSED = "PAUSED"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowCheckpoint(BaseModel):
    """Execution checkpoint representing a safe state boundary in a DAG/workflow."""
    checkpoint_id: str = Field(default_factory=lambda: f"wf-ckpt-{uuid.uuid4().hex[:8]}")
    workflow_id: str
    node_id: str
    state_payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class WorkflowState(BaseModel):
    """Durable state representation for long-running workflows."""
    workflow_id: str = Field(default_factory=lambda: f"wf-{uuid.uuid4().hex[:10]}")
    session_id: str = "default_session"
    task_id: Optional[str] = None
    name: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node: str = ""
    node_states: Dict[str, Any] = Field(default_factory=dict)
    checkpoints: List[WorkflowCheckpoint] = Field(default_factory=list)
    event_history: List[Dict[str, Any]] = Field(default_factory=list)
    retry_policy: Dict[str, Any] = Field(default_factory=lambda: {"max_retries": 3, "backoff_factor": 2.0})
    resume_state: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
