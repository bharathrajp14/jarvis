# agent/task_state.py — Persistent Task State Machine for BR JARVIS MK37
"""
Persistent task state machine and SQLite checkpointing engine for Autonomous Agent 2.0.
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

logger = logging.getLogger("JARVIS.TaskState")

DB_DIR = Path(__file__).resolve().parent.parent / "workspace" / "tasks"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "agent_tasks.db"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
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
    risk_level: str = "medium"  # low, medium, high
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
    status: TaskStatus = TaskStatus.PENDING
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
        d["status"] = self.status.value
        d["actions"] = [a.to_dict() if isinstance(a, TaskAction) else a for a in self.actions]
        if self.approval_request:
            d["approval_request"] = self.approval_request.to_dict() if isinstance(self.approval_request, ApprovalRequest) else self.approval_request
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskState:
        raw = dict(data)
        if "status" in raw and isinstance(raw["status"], str):
            raw["status"] = TaskStatus(raw["status"])
        if "actions" in raw and isinstance(raw["actions"], list):
            raw["actions"] = [TaskAction.from_dict(a) if isinstance(a, dict) else a for a in raw["actions"]]
        if "approval_request" in raw and isinstance(raw["approval_request"], dict):
            raw["approval_request"] = ApprovalRequest.from_dict(raw["approval_request"])
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


class TaskStateManager:
    """SQLite-backed manager for persistent task states and checkpoints."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    active_agents TEXT,
                    active_devices TEXT,
                    data_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at DESC);")
            conn.commit()

    def create_task(self, goal: str, total_steps: int = 0, active_devices: Optional[List[str]] = None) -> TaskState:
        task_id = str(uuid.uuid4())
        devices = active_devices or ["pc"]
        state = TaskState(
            task_id=task_id,
            goal=goal,
            status=TaskStatus.PENDING,
            current_step=0,
            total_steps=total_steps,
            active_devices=devices,
        )
        self.save_task(state)
        logger.info("TaskState: Created task %s for goal: %s", task_id, goal[:60])
        return state

    def save_task(self, state: TaskState) -> None:
        state.updated_at = time.time()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO tasks (
                    task_id, goal, status, current_step, total_steps,
                    active_agents, active_devices, data_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    current_step=excluded.current_step,
                    total_steps=excluded.total_steps,
                    active_agents=excluded.active_agents,
                    active_devices=excluded.active_devices,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
            """, (
                state.task_id,
                state.goal,
                state.status.value,
                state.current_step,
                state.total_steps,
                json.dumps(state.active_agents),
                json.dumps(state.active_devices),
                json.dumps(state.to_dict()),
                state.created_at,
                state.updated_at,
            ))
            conn.commit()

    def get_task(self, task_id: str) -> Optional[TaskState]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data_json FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row:
                return TaskState.from_dict(json.loads(row["data_json"]))
        return None

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[TaskState]:
        with self._get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT data_json FROM tasks WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT data_json FROM tasks ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [TaskState.from_dict(json.loads(r["data_json"])) for r in rows]

    def create_checkpoint(self, task_id: str, step_index: int) -> str:
        state = self.get_task(task_id)
        if not state:
            raise ValueError(f"Task {task_id} not found")
        chk_id = f"chk_{task_id}_{step_index}_{int(time.time())}"
        chk_payload = state.to_dict()
        state.checkpoints.append({"checkpoint_id": chk_id, "step": step_index, "timestamp": time.time()})
        self.save_task(state)

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO checkpoints (checkpoint_id, task_id, step_index, state_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (chk_id, task_id, step_index, json.dumps(chk_payload), time.time()))
            conn.commit()
        return chk_id

    def update_status(self, task_id: str, status: TaskStatus, error_info: Optional[Dict[str, Any]] = None) -> Optional[TaskState]:
        state = self.get_task(task_id)
        if not state:
            return None
        state.status = status
        if error_info:
            state.error_info = error_info
        self.save_task(state)
        return state

    def record_action(self, task_id: str, action: TaskAction) -> Optional[TaskState]:
        state = self.get_task(task_id)
        if not state:
            return None
        state.actions.append(action)
        state.current_step = max(state.current_step, action.step_index)
        self.save_task(state)
        return state

    def request_approval(self, task_id: str, action_id: str, description: str, risk_level: str = "medium", details: Optional[Dict[str, Any]] = None) -> ApprovalRequest:
        state = self.get_task(task_id)
        if not state:
            raise ValueError(f"Task {task_id} not found")
        req_id = str(uuid.uuid4())
        req = ApprovalRequest(
            request_id=req_id,
            task_id=task_id,
            action_id=action_id,
            description=description,
            risk_level=risk_level,
            details=details or {},
            status="pending",
        )
        state.approval_request = req
        state.status = TaskStatus.WAITING_APPROVAL
        self.save_task(state)
        logger.warning("Task %s is WAITING_APPROVAL for action %s: %s", task_id, action_id, description)
        return req

    def resolve_approval(self, task_id: str, request_id: str, approved: bool) -> Optional[TaskState]:
        state = self.get_task(task_id)
        if not state or not state.approval_request:
            return None
        if state.approval_request.request_id != request_id:
            return None
        state.approval_request.status = "approved" if approved else "rejected"
        state.approval_request.resolved_at = time.time()
        state.status = TaskStatus.RUNNING if approved else TaskStatus.FAILED
        if not approved:
            state.error_info = {"reason": "User rejected approval request"}
        self.save_task(state)
        return state


_state_manager_instance: Optional[TaskStateManager] = None


def get_task_state_manager() -> TaskStateManager:
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = TaskStateManager()
    return _state_manager_instance
