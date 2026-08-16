# agent/task_lifecycle.py — Strict Task Lifecycle & Immutable State Machine
"""
Explicit Task State Machine for BR JARVIS.
Defines valid state transitions and guarantees terminal state immutability.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

logger = logging.getLogger("JARVIS.TaskLifecycle")


class TaskState(str, Enum):
    QUEUED     = "queued"
    RUNNING    = "running"
    CANCELLING = "cancelling"
    SUCCEEDED  = "succeeded"
    FAILED     = "failed"
    CANCELLED  = "cancelled"
    TIMED_OUT  = "timed_out"


TERMINAL_STATES: Set[TaskState] = {
    TaskState.SUCCEEDED,
    TaskState.FAILED,
    TaskState.CANCELLED,
    TaskState.TIMED_OUT,
}

# Valid forward transitions
VALID_TRANSITIONS: Dict[TaskState, Set[TaskState]] = {
    TaskState.QUEUED:     {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING:    {TaskState.CANCELLING, TaskState.SUCCEEDED, TaskState.FAILED, TaskState.TIMED_OUT, TaskState.CANCELLED},
    TaskState.CANCELLING: {TaskState.CANCELLED, TaskState.FAILED},
    TaskState.SUCCEEDED:  set(),
    TaskState.FAILED:     set(),
    TaskState.CANCELLED:  set(),
    TaskState.TIMED_OUT:  set(),
}


@dataclass
class CancellationToken:
    """Cooperative cancellation token for tasks and tool executions."""
    _event: threading.Event = field(default_factory=threading.Event)
    _reason: str = ""

    def cancel(self, reason: str = "User requested cancellation") -> None:
        self._reason = reason
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason

    def check(self) -> None:
        """Raise InterruptedError if cancelled."""
        if self.is_cancelled:
            raise InterruptedError(f"Task cancelled: {self._reason}")


@dataclass
class TaskContext:
    """Complete structured context for a managed task."""
    task_id: str
    goal: str
    priority: int = 2
    state: TaskState = TaskState.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0
    timeout_s: float = 300.0
    result: Any = None
    error: Optional[str] = None
    cancellation_token: CancellationToken = field(default_factory=CancellationToken)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def transition_to(self, target_state: TaskState, error_msg: Optional[str] = None) -> bool:
        """Transition task to a new state if permitted by the state machine.
        Terminal states can NEVER transition to any other state.
        """
        with self._lock:
            if self.state in TERMINAL_STATES:
                logger.warning(
                    "Illegal state transition attempted for task %s: from terminal state '%s' to '%s'",
                    self.task_id, self.state.value, target_state.value
                )
                return False

            allowed = VALID_TRANSITIONS.get(self.state, set())
            if target_state not in allowed:
                logger.warning(
                    "Invalid state transition for task %s: '%s' -> '%s'",
                    self.task_id, self.state.value, target_state.value
                )
                return False

            self.state = target_state
            now = time.time()
            if target_state == TaskState.RUNNING and not self.started_at:
                self.started_at = now
            elif target_state in TERMINAL_STATES and not self.finished_at:
                self.finished_at = now

            if error_msg:
                self.error = error_msg

            logger.info("Task %s transitioned: -> %s", self.task_id, target_state.value)
            return True

    @property
    def duration_s(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.finished_at or time.time()
        return round(end - self.started_at, 2)
