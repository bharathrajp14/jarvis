# core/execution/trace.py — Universal Execution Trace & Telemetry Engine
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .types import ExecutionStatus

logger = logging.getLogger("JARVIS.ExecutionTrace")

_SECRET_PATTERNS = [
    re.compile(r"(AIzaSy[0-9A-Za-z\-_]{33})"),
    re.compile(r"(sk-[a-zA-Z0-9_\-]{20,})"),
    re.compile(r"(ghp_[a-zA-Z0-9]{36})"),
    re.compile(r"(Bearer\s+[a-zA-Z0-9_\-\.]{20,})"),
]


def redact_secrets(text: str) -> str:
    """Redact API keys, tokens, and secrets from traces."""
    if not isinstance(text, str):
        return text
    clean = text
    for p in _SECRET_PATTERNS:
        clean = p.sub(r"[\1_REDACTED]", clean)
    return clean


@dataclass
class TraceEvent:
    stage: str  # REQUEST, PLAN, CAPABILITY, ENVIRONMENT, DEPENDENCY, EXECUTION, VALIDATION, VERIFICATION, RECOVERY, GATE, FINAL_STATUS
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "message": redact_secrets(self.message),
            "data": {k: redact_secrets(str(v)) if isinstance(v, str) else v for k, v in self.data.items()},
            "timestamp": self.timestamp,
        }


class ExecutionTrace:
    """
    Developer Trace & Evidence Collector.
    Allows end-to-end tracing of 'Why did JARVIS reach this conclusion?'
    """

    def __init__(self, task_id: str, goal: str):
        self.task_id = task_id
        self.goal = goal
        self.events: List[TraceEvent] = []
        self.started_at = time.time()
        self.completed_at: Optional[float] = None
        self.final_status: ExecutionStatus = ExecutionStatus.SUCCESS_UNVERIFIED

        self.add_event("REQUEST", f"Task initialized: '{goal}'", {"task_id": task_id})

    def add_event(self, stage: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        event = TraceEvent(stage=stage.upper(), message=message, data=data or {})
        self.events.append(event)
        logger.debug(f"[Trace:{self.task_id}] [{stage.upper()}] {message}")

    def complete(self, status: ExecutionStatus, summary: str = "") -> None:
        self.completed_at = time.time()
        self.final_status = status
        self.add_event("FINAL_STATUS", f"Task finished with status {status.value}: {summary}", {"status": status.value})

    def format_timeline(self) -> str:
        """Render a readable developer trace timeline."""
        lines = [f"=== Universal Execution Trace [{self.task_id}] ===", f"Goal: {self.goal}"]
        for e in self.events:
            elapsed = (e.timestamp - self.started_at) * 1000.0
            lines.append(f"[{elapsed:6.1f}ms] [{e.stage:<14}] {e.message}")
        lines.append(f"Final Status: {self.final_status.value}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": redact_secrets(self.goal),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": int(((self.completed_at or time.time()) - self.started_at) * 1000),
            "final_status": self.final_status.value,
            "events": [e.to_dict() for e in self.events],
        }
