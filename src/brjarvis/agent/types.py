# agent/types.py — Pydantic v2 Data Models for JARVIS MK37 Planner & Executor
from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StepStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskStepNode(BaseModel):
    step_id: int
    tool: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[int] = Field(default_factory=list)
    parallel: bool = False
    critical: bool = True
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class GoalGraph(BaseModel):
    goal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    goal: str
    steps: List[TaskStepNode] = Field(default_factory=list)
    can_parallelize: bool = False
    estimated_time_s: float = 0.0
    estimated_token_cost: int = 0
    requires_user_confirmation: bool = False
    created_at: float = Field(default_factory=time.time)


class ExecutionReport(BaseModel):
    goal_id: str
    status: str  # SUCCESS, FAILED, PARTIAL
    completed_steps: int
    total_steps: int
    duration_s: float
    error_summary: Optional[str] = None
