# reasoning/types.py — Data Models for JARVIS MK37 Reasoning Engine
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ConfidenceScore:
    """Confidence breakdown score for a planned decision or action."""

    overall: float  # 0.0 to 1.0
    reasoning_quality: float  # 0.0 to 1.0
    tool_match_score: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high", "critical"

    def requires_approval(self) -> bool:
        return self.risk_level in ("high", "critical") or self.overall < 0.6


@dataclass
class TaskNode:
    """A node in the execution PlanGraph."""

    id: int
    title: str
    description: str
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[int] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    confidence: Optional[ConfidenceScore] = None


@dataclass
class PlanGraph:
    """A Directed Acyclic Graph (DAG) representing a planned task execution."""

    goal: str
    nodes: List[TaskNode] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    parallelizable: bool = False

    def get_node(self, node_id: int) -> Optional[TaskNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_ready_nodes(self, completed_ids: set[int]) -> List[TaskNode]:
        """Return nodes whose dependencies are all satisfied."""
        ready = []
        for node in self.nodes:
            if node.status == StepStatus.PENDING:
                if all(dep in completed_ids for dep in node.depends_on):
                    ready.append(node)
        return ready


@dataclass
class ReasoningStep:
    """A single step in a Chain-of-Thought reasoning trace."""

    thought: str
    action_type: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    confidence: float = 1.0


@dataclass
class ReasoningTrace:
    """Full Chain-of-Thought trace for auditing and self-verification."""

    goal: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    verified: bool = False
    verification_notes: Optional[str] = None
