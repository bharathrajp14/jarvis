# memory/lessons.py — Persistent Lesson & Correction Store
"""
LessonStore for storing and semantically retrieving explicit and implicit user corrections.
Used by ContextEngine and Task Planner to prevent repeating errors and enforce learned rules.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.LessonStore")

LESSONS_DB_FILE = paths.MEMORY_ROOT / "lessons.db"


class LessonStore:
    """Stores and retrieves user corrections, architectural lessons, and adaptive weights."""

    def __init__(self, db_path: Path = LESSONS_DB_FILE):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Return a reusable WAL-enabled connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=20.0,
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=20000")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    correction TEXT NOT NULL,
                    source TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    created_at REAL NOT NULL,
                    last_retrieved_at REAL
                )
                """
            )
            conn.commit()

    def add_lesson(
        self, topic: str, correction: str, source: str = "explicit", weight: float = 1.0
    ) -> int:
        """Add a correction lesson to the database."""
        return self.store_lesson(topic, correction, source, weight)

    def store_lesson(
        self,
        topic: str,
        correction: str,
        source: str = "user_correction",
        weight: float = 1.0,
    ) -> int:
        """Store a new lesson learned from a user correction or operational feedback."""
        def _do_write():
            with self._lock:
                conn = self._get_conn()
                cur = conn.execute(
                    """
                    INSERT INTO lessons (topic, correction, source, weight, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (topic, correction, source, weight, time.time()),
                )
                conn.commit()
                return cur.lastrowid or 0

        from memory.sqlite_lock import run_sqlite_write
        return run_sqlite_write(_do_write)

    def strengthen_lesson(self, lesson_id: int, factor: float = 1.25) -> bool:
        """Increase lesson weight when it successfully prevents an error or guides a task."""
        with self._lock:
            conn = self._get_conn()
            cur = conn.execute(
                "UPDATE lessons SET weight = MIN(5.0, weight * ?) WHERE id = ?",
                (factor, lesson_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def weaken_lesson(self, lesson_id: int, factor: float = 0.80) -> bool:
        """Decrease lesson weight if it is superseded or contradicted by newer feedback."""
        with self._lock:
            conn = self._get_conn()
            cur = conn.execute(
                "UPDATE lessons SET weight = MAX(0.1, weight * ?) WHERE id = ?",
                (factor, lesson_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_lesson(self, lesson_id: int) -> bool:
        """Delete an obsolete lesson from the database."""
        with self._lock:
            conn = self._get_conn()
            cur = conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_relevant_lessons(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant lessons matching query keywords with score ranking."""
        query_words = [w.lower() for w in query.split() if len(w) >= 2]
        if not query_words:
            return self.get_latest_lessons(limit=limit)

        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM lessons ORDER BY weight DESC, created_at DESC LIMIT 100"
            ).fetchall()

            matched = []
            for row in rows:
                try:
                    topic_val = row["topic"] if "topic" in row.keys() else ""
                    corr_val = row["correction"] if "correction" in row.keys() else ""
                    src_val = row["source"] if "source" in row.keys() else ""
                    text = f"{topic_val} {corr_val} {src_val}".lower()
                    score = sum(1 for w in query_words if w in text)
                    if score > 0:
                        item = dict(row)
                        matched.append((score * float(row["weight"] or 1.0), item))
                except Exception:
                    continue

            matched.sort(key=lambda x: x[0], reverse=True)
            return [m[1] for m in matched[:limit]]

    def get_latest_lessons(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get latest lessons sorted by timestamp."""
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM lessons ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def record_workflow_lesson(self, workflow_name: str, sequence_desc: str, success: bool = True) -> int:
        """Record verified multi-tool workflow sequence pattern to memory."""
        topic = f"workflow.{workflow_name.lower().replace(' ', '_')}"
        status_tag = "SUCCESS" if success else "FAILURE"
        correction = f"[{status_tag}] Workflow sequence: {sequence_desc}"
        return self.store_lesson(topic=topic, correction=correction, source="workflow_orchestrator", weight=1.5 if success else 0.8)

    def get_workflow_patterns(self, query: str = "") -> List[Dict[str, Any]]:
        """Retrieve verified workflow lessons."""
        return self.get_relevant_lessons(f"workflow {query}", limit=5)
