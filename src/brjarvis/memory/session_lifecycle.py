# memory/session_lifecycle.py — Non-Destructive Session Memory & Cross-Session State Recovery
"""
Session Lifecycle and Cross-Session Recovery Engine for BR JARVIS.
Replaces destructive `pop_last_session()` with non-destructive state:
  Read -> Acknowledge -> Mark Consumed
Preserves full historical audit logs of previous sessions.
Allows a new process to reconstruct:
- What project were we working on?
- What was the last important decision?
- What remains unfinished?
- What failed previously?
- What should happen next?
- What constraints did the user specify?
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .canonical_db import CanonicalDatabaseManager, get_canonical_db

logger = logging.getLogger("JARVIS.SessionLifecycle")


@dataclass
class SessionRecord:
    """Complete structured record of a single interactive or background session."""

    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    summary: str = ""
    goals: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    unfinished_tasks: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    successful_actions: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    consumed: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionRecord:
        d = dict(data)
        for list_field in (
            "goals",
            "decisions",
            "constraints",
            "unfinished_tasks",
            "errors",
            "successful_actions",
            "next_actions",
        ):
            if list_field in d and isinstance(d[list_field], str):
                try:
                    d[list_field] = json.loads(d[list_field])
                except Exception:
                    d[list_field] = []
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


class SessionLifecycleManager:
    """Manages persistent, non-destructive session records across process restarts."""

    def __init__(self, db_manager: Optional[CanonicalDatabaseManager] = None):
        self.db = db_manager or get_canonical_db()

    def save_session(self, record: SessionRecord) -> SessionRecord:
        """Persist or update a session record in the canonical database."""
        with self.db.get_connection() as conn:
            record.updated_at = time.time()
            conn.execute(
                """
                INSERT INTO session_records (
                    session_id, start_time, end_time, summary, goals_json, decisions_json,
                    constraints_json, unfinished_tasks_json, errors_json, successful_actions_json,
                    next_actions_json, consumed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    end_time = excluded.end_time,
                    summary = excluded.summary,
                    goals_json = excluded.goals_json,
                    decisions_json = excluded.decisions_json,
                    constraints_json = excluded.constraints_json,
                    unfinished_tasks_json = excluded.unfinished_tasks_json,
                    errors_json = excluded.errors_json,
                    successful_actions_json = excluded.successful_actions_json,
                    next_actions_json = excluded.next_actions_json,
                    consumed = excluded.consumed,
                    updated_at = excluded.updated_at
                """,
                (
                    record.session_id,
                    record.start_time,
                    record.end_time,
                    record.summary,
                    json.dumps(record.goals),
                    json.dumps(record.decisions),
                    json.dumps(record.constraints),
                    json.dumps(record.unfinished_tasks),
                    json.dumps(record.errors),
                    json.dumps(record.successful_actions),
                    json.dumps(record.next_actions),
                    1 if record.consumed else 0,
                    record.created_at,
                    record.updated_at,
                ),
            )
            conn.commit()
        return record

    def get_last_unconsumed_session(self) -> Optional[SessionRecord]:
        """Retrieve the most recent session that hasn't been acknowledged/briefed yet (non-destructive)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM session_records WHERE consumed = 0 ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def acknowledge_session(self, session_id: str) -> bool:
        """Mark a session record as consumed without deleting it from history."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE session_records SET consumed = 1, updated_at = ? WHERE session_id = ?",
                (time.time(), session_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_recent_sessions(self, limit: int = 10) -> List[SessionRecord]:
        """List historical sessions for briefing and state reconstruction."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM session_records ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            return [self._row_to_record(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_record(row: Any) -> SessionRecord:
        return SessionRecord(
            session_id=row["session_id"],
            start_time=float(row["start_time"]),
            end_time=float(row["end_time"]) if row["end_time"] is not None else None,
            summary=row["summary"] or "",
            goals=json.loads(row["goals_json"] or "[]"),
            decisions=json.loads(row["decisions_json"] or "[]"),
            constraints=json.loads(row["constraints_json"] or "[]"),
            unfinished_tasks=json.loads(row["unfinished_tasks_json"] or "[]"),
            errors=json.loads(row["errors_json"] or "[]"),
            successful_actions=json.loads(row["successful_actions_json"] or "[]"),
            next_actions=json.loads(row["next_actions_json"] or "[]"),
            consumed=bool(row["consumed"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )


_GLOBAL_SESSION_MANAGER: Optional[SessionLifecycleManager] = None


def get_session_lifecycle_manager() -> SessionLifecycleManager:
    """Return singleton SessionLifecycleManager."""
    global _GLOBAL_SESSION_MANAGER
    if _GLOBAL_SESSION_MANAGER is None:
        _GLOBAL_SESSION_MANAGER = SessionLifecycleManager()
    return _GLOBAL_SESSION_MANAGER
