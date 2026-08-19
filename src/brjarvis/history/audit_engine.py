# history/audit_engine.py — Structured Audit Logging & Replay Engine
"""
Structured Audit Logging Engine for BR JARVIS MK37.
Captures every sensitive action with task ID, device ID, application, risk level,
approval source, timestamps, and execution results. Supports search, filter, and replay.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.AuditEngine")

DB_DIR = paths.WORKSPACE_ROOT / "audit"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "audit_events.db"


@dataclass
class AuditEvent:
    event_id: str
    task_id: str
    device_id: str
    application: str
    action: str
    risk: str = "low"  # low, medium, high
    approval: str = "auto"  # auto, user, policy
    details: Dict[str, Any] = field(default_factory=dict)
    result: str = "success"
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditEvent:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AuditEngine:
    """SQLite-backed structured audit logger."""

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
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    application TEXT NOT NULL,
                    action TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    approval TEXT NOT NULL,
                    details_json TEXT,
                    result TEXT NOT NULL,
                    duration REAL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_events(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);")
            conn.commit()

    def log_event(
        self,
        task_id: str,
        device_id: str,
        application: str,
        action: str,
        risk: str = "low",
        approval: str = "auto",
        details: Optional[Dict[str, Any]] = None,
        result: str = "success",
        duration: float = 0.0,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            device_id=device_id,
            application=application,
            action=action,
            risk=risk,
            approval=approval,
            details=details or {},
            result=result,
            duration=duration,
            timestamp=time.time(),
        )
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    event_id, task_id, device_id, application, action, risk, approval, details_json, result, duration, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.event_id,
                    event.task_id,
                    event.device_id,
                    event.application,
                    event.action,
                    event.risk,
                    event.approval,
                    json.dumps(event.details),
                    event.result,
                    event.duration,
                    event.timestamp,
                ),
            )
            conn.commit()
        return event

    def query_events(
        self,
        task_id: Optional[str] = None,
        device_id: Optional[str] = None,
        risk: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        with self._get_conn() as conn:
            clauses = []
            params: List[Any] = []
            if task_id:
                clauses.append("task_id = ?")
                params.append(task_id)
            if device_id:
                clauses.append("device_id = ?")
                params.append(device_id)
            if risk:
                clauses.append("risk = ?")
                params.append(risk)

            where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            query = f"SELECT * FROM audit_events {where_str} ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            events = []
            for r in rows:
                d = dict(r)
                d["details"] = json.loads(d["details_json"]) if d.get("details_json") else {}
                del d["details_json"]
                events.append(AuditEvent.from_dict(d))
            return events


_audit_engine_instance: Optional[AuditEngine] = None


def get_audit_engine() -> AuditEngine:
    global _audit_engine_instance
    if _audit_engine_instance is None:
        _audit_engine_instance = AuditEngine()
    return _audit_engine_instance
