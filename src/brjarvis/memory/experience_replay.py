# memory/experience_replay.py — Trajectory Experience Replay Database for BR JARVIS MK38
"""
Stores complete execution trajectories (successful vs failed steps) in SQLite WAL database
for trajectory playback, similarity retrieval, and few-shot in-context learning.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .persistent_store import get_memory_dir

logger = logging.getLogger("JARVIS.ExperienceReplay")


class ExperienceTrajectory(BaseModel):
    """Structured execution trajectory record."""

    trajectory_id: str = Field(default_factory=lambda: f"traj-{uuid.uuid4().hex[:12]}")
    goal_query: str
    success_status: bool
    step_count: int
    tool_sequence: List[str] = Field(default_factory=list)
    failure_reason: Optional[str] = None
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class ExperienceReplayStore:
    """
    SQLite WAL-backed Experience Replay database for storing and retrieving past execution patterns.
    """

    def __init__(self, db_dir: Optional[Path] = None):
        if db_dir is None:
            db_dir = get_memory_dir("user")
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "experience_replay.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=20.0,
            )
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA busy_timeout=20000;")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experience_trajectories (
                    trajectory_id TEXT PRIMARY KEY,
                    goal_query TEXT NOT NULL,
                    success_status INTEGER NOT NULL,
                    step_count INTEGER NOT NULL,
                    tool_sequence TEXT NOT NULL,
                    failure_reason TEXT,
                    execution_context TEXT,
                    created_at REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trajectories_status ON experience_trajectories(success_status);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trajectories_created ON experience_trajectories(created_at);
            """)
        logger.info(f"💾 ExperienceReplayStore initialized at {self.db_path}")

    def record_trajectory(self, trajectory: ExperienceTrajectory) -> None:
        """Persist an execution trajectory record."""

        def _do_write():
            conn = self._get_conn()
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO experience_trajectories (
                        trajectory_id, goal_query, success_status, step_count,
                        tool_sequence, failure_reason, execution_context, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trajectory.trajectory_id,
                        trajectory.goal_query,
                        1 if trajectory.success_status else 0,
                        trajectory.step_count,
                        json.dumps(trajectory.tool_sequence),
                        trajectory.failure_reason,
                        json.dumps(trajectory.execution_context),
                        trajectory.created_at,
                    ),
                )

        from brjarvis.memory.sqlite_lock import run_sqlite_write

        run_sqlite_write(_do_write)
        logger.debug(f"Recorded trajectory {trajectory.trajectory_id} (Success: {trajectory.success_status})")

    def get_similar_failures(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent failed trajectories matching query keywords."""
        conn = self._get_conn()
        words = [w.lower() for w in query.split() if len(w) > 3]
        if not words:
            cursor = conn.execute(
                "SELECT * FROM experience_trajectories WHERE success_status = 0 ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        else:
            like_clause = " OR ".join(["LOWER(goal_query) LIKE ?"] * len(words))
            params = [f"%{w}%" for w in words] + [limit]
            cursor = conn.execute(
                f"SELECT * FROM experience_trajectories WHERE success_status = 0 AND ({like_clause}) ORDER BY created_at DESC LIMIT ?",
                params,
            )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "trajectory_id": row["trajectory_id"],
                    "goal_query": row["goal_query"],
                    "step_count": row["step_count"],
                    "tool_sequence": json.loads(row["tool_sequence"] or "[]"),
                    "failure_reason": row["failure_reason"],
                    "created_at": row["created_at"],
                }
            )
        return results

    def get_successful_patterns(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent successful execution trajectories matching query keywords."""
        conn = self._get_conn()
        words = [w.lower() for w in query.split() if len(w) > 3]
        if not words:
            cursor = conn.execute(
                "SELECT * FROM experience_trajectories WHERE success_status = 1 ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        else:
            like_clause = " OR ".join(["LOWER(goal_query) LIKE ?"] * len(words))
            params = [f"%{w}%" for w in words] + [limit]
            cursor = conn.execute(
                f"SELECT * FROM experience_trajectories WHERE success_status = 1 AND ({like_clause}) ORDER BY created_at DESC LIMIT ?",
                params,
            )

        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "trajectory_id": row["trajectory_id"],
                    "goal_query": row["goal_query"],
                    "step_count": row["step_count"],
                    "tool_sequence": json.loads(row["tool_sequence"] or "[]"),
                    "created_at": row["created_at"],
                }
            )
        return results

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


_global_experience_replay: Optional[ExperienceReplayStore] = None


def get_experience_replay() -> ExperienceReplayStore:
    global _global_experience_replay
    if _global_experience_replay is None:
        _global_experience_replay = ExperienceReplayStore()
    return _global_experience_replay
