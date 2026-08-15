# agent/task_state.py — Persistent Task State Machine for BR JARVIS
"""
Persistent task state machine and SQLite WAL checkpointing engine for Autonomous Agent Control Plane.
Tracks full lifecycle: Goal -> Planning -> Tool/Device Selection -> Execution -> Observe -> Verify -> Complete.
Supports pause, resume, cancel, retry, checkpoints, recovery, and approval gates.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from memory.canonical_db import get_canonical_db

logger = logging.getLogger("JARVIS.TaskState")


class TaskStatus(str, Enum):
    PENDING = "pending"
    CREATED = "created"
    VALIDATING = "validating"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_FOR_APPROVAL = "waiting_approval"
    WAITING_FOR_DEVICE = "waiting_for_device"
    WAITING_FOR_AUTH = "waiting_for_auth"
    WAITING_FOR_USER = "waiting_for_user"
    RECOVERING = "recovering"
    RETRYING = "retrying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskAction:
    action_id: str
    step_index: int
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_device: str = "pc"
    target_app: str = ""
    status: str = "pending"
    result: str = ""
    error: str = ""
    verified: bool = False
    verification_notes: str = ""
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskAction:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ApprovalRequest:
    request_id: str
    task_id: str
    action_id: str
    description: str
    risk_level: str = "medium"  # low, medium, high, critical
    details: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"     # pending, approved, rejected
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApprovalRequest:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TaskState:
    task_id: str
    goal: str
    request_id: str = ""
    parent_task_id: str = ""
    cancellation_requested: bool = False
    status: TaskStatus = TaskStatus.CREATED
    current_step: int = 0
    total_steps: int = 0
    plan: Dict[str, Any] = field(default_factory=dict)
    active_agents: List[str] = field(default_factory=list)
    active_devices: List[str] = field(default_factory=lambda: ["pc"])
    actions: List[TaskAction] = field(default_factory=list)
    approval_request: Optional[ApprovalRequest] = None
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    error_info: Optional[Dict[str, Any]] = None
    final_report: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, TaskStatus) else str(self.status)
        d["actions"] = [a.to_dict() if isinstance(a, TaskAction) else a for a in self.actions]
        if self.approval_request:
            d["approval_request"] = self.approval_request.to_dict() if isinstance(self.approval_request, ApprovalRequest) else self.approval_request
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskState:
        raw = dict(data)
        if "status" in raw and isinstance(raw["status"], str):
            try:
                raw["status"] = TaskStatus(raw["status"])
            except ValueError:
                raw["status"] = TaskStatus.RUNNING if raw["status"] == "running" else TaskStatus.CREATED
        if "actions" in raw and isinstance(raw["actions"], list):
            raw["actions"] = [TaskAction.from_dict(a) if isinstance(a, dict) else a for a in raw["actions"]]
        if "approval_request" in raw and isinstance(raw["approval_request"], dict):
            raw["approval_request"] = ApprovalRequest.from_dict(raw["approval_request"])
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


class TaskStateManager:
    """SQLite WAL-backed manager for persistent task states, steps, and checkpoints."""

    def __init__(self, db_manager=None, db_path: Optional[Path | str] = None):
        if db_path is not None:
            from memory.canonical_db import CanonicalDatabaseManager
            self.db_manager = CanonicalDatabaseManager(db_path=Path(db_path))
        else:
            self.db_manager = db_manager or get_canonical_db()

    def _get_conn(self) -> sqlite3.Connection:
        return self.db_manager.get_connection()

    def create_task(self, goal: str, total_steps: int = 0, active_devices: Optional[List[str]] = None, task_id: Optional[str] = None) -> TaskState:
        """Initialize and persist a new autonomous task."""
        tid = task_id or f"task_{uuid.uuid4().hex[:12]}"
        now = time.time()
        devices = active_devices or ["pc"]

        state = TaskState(
            task_id=tid,
            goal=goal,
            status=TaskStatus.CREATED,
            total_steps=total_steps,
            active_devices=devices,
            created_at=now,
            updated_at=now
        )

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks (task_id, goal, status, current_step, total_steps, active_agents, active_devices, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.task_id,
                    state.goal,
                    state.status.value,
                    state.current_step,
                    state.total_steps,
                    json.dumps(state.active_agents),
                    json.dumps(state.active_devices),
                    json.dumps(state.to_dict()),
                    state.created_at,
                    state.updated_at
                )
            )
            conn.commit()

        logger.info("Created Task [%s]: '%s'", state.task_id, goal[:60])
        return state

    def record_action(self, task_id: str, action: TaskAction) -> None:
        """Record an executed action to the task history."""
        task = self.get_task(task_id)
        if task:
            task.actions.append(action)
            task.current_step = max(task.current_step, action.step_index)
            self.save_task(task)

    def update_status(self, task_id: str, status: TaskStatus, error_info: Optional[Dict[str, Any]] = None) -> Optional[TaskState]:
        """Update overall task status with timestamp and optional error payload."""
        return self.update_task_status(task_id, status, error_info)

    def update_task_status(self, task_id: str, status: TaskStatus, error_info: Optional[Dict[str, Any]] = None) -> Optional[TaskState]:
        """Update overall task status with timestamp and optional error payload."""
        state = self.get_task(task_id)
        if not state:
            return None

        state.status = status
        state.updated_at = time.time()
        if error_info:
            state.error_info = error_info

        self.save_task(state)
        logger.info("Task [%s] transition -> %s", task_id, status.value if hasattr(status, 'value') else status)
        return state

    def save_task(self, state: TaskState) -> None:
        """Persist full TaskState snapshot to SQLite."""
        state.updated_at = time.time()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks (task_id, goal, status, current_step, total_steps, active_agents, active_devices, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.task_id,
                    state.goal,
                    state.status.value if isinstance(state.status, TaskStatus) else str(state.status),
                    state.current_step,
                    state.total_steps,
                    json.dumps(state.active_agents),
                    json.dumps(state.active_devices),
                    json.dumps(state.to_dict()),
                    state.created_at,
                    state.updated_at
                )
            )
            conn.commit()

    def get_task(self, task_id: str) -> Optional[TaskState]:
        """Retrieve task by ID."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT data_json FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            try:
                data = json.loads(row["data_json"])
                return TaskState.from_dict(data)
            except Exception as e:
                logger.error("Error deserializing task [%s]: %s", task_id, e)
                return None

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[TaskState]:
        """List active and historical tasks."""
        with self._get_conn() as conn:
            if status:
                cursor = conn.execute("SELECT data_json FROM tasks WHERE status = ? ORDER BY updated_at DESC LIMIT ?", (status, limit))
            else:
                cursor = conn.execute("SELECT data_json FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            tasks = []
            for r in rows:
                try:
                    tasks.append(TaskState.from_dict(json.loads(r["data_json"])))
                except Exception:
                    pass
            return tasks

    def record_step_wal(
        self,
        task_id: str,
        step_index: int,
        capability: str,
        parameters: Dict[str, Any],
        status: str = "running",
        result: Optional[Any] = None,
        error: Optional[str] = None,
        duration: float = 0.0,
        verified: bool = False
    ) -> str:
        """Write-Ahead Log step transition to task_steps table before and after tool execution."""
        step_id = f"{task_id}_s{step_index}_{int(time.time() * 1000)}"
        now = time.time()
        with self._get_conn() as conn:
            # Ensure parent task exists to satisfy foreign key constraint
            conn.execute(
                """
                INSERT OR IGNORE INTO tasks (task_id, goal, status, current_step, total_steps, active_agents, active_devices, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    f"Auto-task {task_id}",
                    "running",
                    step_index,
                    0,
                    "[]",
                    "[\"pc\"]",
                    json.dumps({"task_id": task_id, "goal": f"Auto-task {task_id}", "status": "running"}),
                    now,
                    now
                )
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO task_steps (step_id, task_id, step_index, capability, parameters_json, status, result_json, error_msg, verified, duration, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_id,
                    task_id,
                    step_index,
                    capability,
                    json.dumps(parameters, default=str),
                    status,
                    json.dumps(result, default=str) if result is not None else None,
                    error,
                    1 if verified else 0,
                    duration,
                    now,
                    now
                )
            )
            conn.commit()
        return step_id

    def create_checkpoint(self, task_id: str, step_index: int) -> str:
        """Save a rollback checkpoint snapshot for the current step."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found for checkpoint")

        chk_id = f"chk_{task_id}_{step_index}_{int(time.time())}"
        snapshot_json = json.dumps(task.to_dict())

        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (checkpoint_id, task_id, step_index, state_snapshot, created_at) VALUES (?, ?, ?, ?, ?)",
                (chk_id, task_id, step_index, snapshot_json, time.time())
            )
            conn.commit()

        task.checkpoints.append({"checkpoint_id": chk_id, "step_index": step_index, "created_at": time.time()})
        self.save_task(task)
        logger.info("Saved Checkpoint [%s] at Step #%d for Task [%s]", chk_id, step_index, task_id)
        return chk_id

    def request_approval(self, task_id: str, action_id: str, description: str, risk_level: str = "medium", details: Optional[Dict[str, Any]] = None) -> ApprovalRequest:
        """Pause task execution and register an approval gate."""
        req_id = f"appr_{uuid.uuid4().hex[:8]}"
        req = ApprovalRequest(
            request_id=req_id,
            task_id=task_id,
            action_id=action_id,
            description=description,
            risk_level=risk_level,
            details=details or {}
        )

        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.WAITING_FOR_APPROVAL
            task.approval_request = req
            self.save_task(task)

        logger.warning("Approval Required for Task [%s]: %s (Risk: %s)", task_id, description, risk_level)
        return req

    def resolve_approval(self, task_id: str, request_id: str, approved: bool) -> Optional[TaskState]:
        """Approve or reject a pending approval request."""
        task = self.get_task(task_id)
        if not task or not task.approval_request:
            return None

        if task.approval_request.request_id == request_id:
            task.approval_request.status = "approved" if approved else "rejected"
            task.approval_request.resolved_at = time.time()
            task.status = TaskStatus.RUNNING if approved else TaskStatus.CANCELLED
            self.save_task(task)
            logger.info("Resolved Approval [%s] for Task [%s]: %s", request_id, task_id, task.approval_request.status)
            return task
        return None


_GLOBAL_TASK_STATE_MGR: Optional[TaskStateManager] = None


def get_task_state_manager() -> TaskStateManager:
    """Return the global TaskStateManager instance."""
    global _GLOBAL_TASK_STATE_MGR
    if _GLOBAL_TASK_STATE_MGR is None:
        _GLOBAL_TASK_STATE_MGR = TaskStateManager()
    return _GLOBAL_TASK_STATE_MGR
