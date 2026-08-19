# src/brjarvis/contracts/task.py — Canonical Task Contracts for BR JARVIS
"""
Canonical Task contracts for BR JARVIS operating runtime.
Defines TaskStatus, TaskCriterion, TaskAction, ApprovalRequest, Task, and TaskState.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Canonical Task Lifecycle Statuses."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskCriterion(BaseModel):
    """Discrete requirement criterion (e.g. C1 = File created, C2 = Window focused)."""
    criterion_id: str = Field(default_factory=lambda: f"crit-{uuid.uuid4().hex[:6]}")
    description: str
    required: bool = True
    status: str = Field(default="PENDING", description="PENDING, VERIFIED, FAILED, UNVERIFIED")
    evidence: str = ""


class TaskAction(BaseModel):
    """Discrete executable step or tool call within a task."""
    action_id: str = Field(default_factory=lambda: f"act-{uuid.uuid4().hex[:8]}")
    step_index: int = 0
    tool: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    target_device: str = "pc"
    target_app: str = ""
    status: str = Field(default="pending", description="pending, running, completed, failed, skipped")
    result: str = ""
    error: str = ""
    verified: bool = False
    verification_notes: str = ""
    duration_ms: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class ApprovalRequest(BaseModel):
    """Interactive permission or security approval request."""
    request_id: str = Field(default_factory=lambda: f"appr-{uuid.uuid4().hex[:8]}")
    task_id: str
    action_id: str = ""
    description: str
    risk_level: str = "medium"  # low, medium, high, critical
    required_role: str = "user"
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED
    decision: Optional[str] = None
    decided_by: str = ""
    decided_at: Optional[float] = None
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None


class Task(BaseModel):
    """Canonical Task Model for BR JARVIS."""
    task_id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:10]}")
    goal_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    agent_id: str = "jarvis-general"
    session_id: str = "default_session"
    project_id: str = "global"
    workspace_id: str = "default"
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Field(default=5, description="1 (lowest) to 10 (highest)")
    description: str
    constraints: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    criteria: List[TaskCriterion] = Field(default_factory=list)
    actions: List[TaskAction] = Field(default_factory=list)
    budget: Dict[str, Any] = Field(default_factory=dict)
    deadline: Optional[float] = None
    current_step: int = 0
    checkpoint_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[str] = None
    failure_reason: Optional[str] = None
    verification_evidence: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskState(BaseModel):
    """Durable state representation of an executing or suspended task."""
    task_id: str
    session_id: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    steps_total: int = 0
    steps_completed: int = 0
    current_step_index: int = 0
    actions: List[TaskAction] = Field(default_factory=list)
    criteria: List[TaskCriterion] = Field(default_factory=list)
    active_approval: Optional[ApprovalRequest] = None
    checkpoint_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
