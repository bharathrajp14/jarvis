# memory/conversation_store.py — SQLite Conversation History
"""
SQLite-backed conversation history store for JARVIS MK37.
Replaces slow file-based audits/sessions with queryable database storage.
"""
from __future__ import annotations

import sqlite3
import time
import json
from pathlib import Path
from typing import Any

from memory.persistent_store import get_memory_dir


class ConversationStore:
    """Manages recording and querying session and turn history in SQLite."""

    def __init__(self):
        # Place database inside the user memory scope
        db_dir = get_memory_dir("user")
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "conversation_history.db"
        self._conn: sqlite3.Connection | None = None
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
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                mode TEXT,
                backend TEXT,
                summary TEXT,
                mtime REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                role TEXT,
                content TEXT,
                tool_name TEXT,
                tool_args TEXT,
                tool_result TEXT,
                latency_ms INTEGER,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        """)
        conn.commit()

    def _execute_write(self, sql: str, params: tuple = ()) -> None:
        """Execute a write statement with automatic retry on database lock."""
        for attempt in range(5):
            try:
                conn = self._get_conn()
                conn.execute(sql, params)
                conn.commit()
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise
            except Exception as e:
                print(f"[ConversationStore] Write error: {e}")
                return

    def start_session(self, session_id: str, mode: str = "general", backend: str = "gemini") -> None:
        """Start recording a new session."""
        self._execute_write(
            """
            INSERT OR REPLACE INTO sessions (id, start_time, mode, backend, summary, mtime)
            VALUES (?, datetime('now', 'localtime'), ?, ?, '', ?)
            """,
            (session_id, mode, backend, time.time())
        )

    def end_session(self, session_id: str, summary: str = "") -> None:
        """End a session and record its summary consolidation."""
        self._execute_write(
            """
            UPDATE sessions 
            SET end_time = datetime('now', 'localtime'), summary = ?, mtime = ?
            WHERE id = ?
            """,
            (summary, time.time(), session_id)
        )

    def log_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_args: dict | None = None,
        tool_result: str | None = None,
        latency_ms: int = 0
    ) -> None:
        """Log an individual message exchange turn in the active session."""
        args_str = json.dumps(tool_args) if tool_args else None
        self._execute_write(
            """
            INSERT INTO turns (session_id, timestamp, role, content, tool_name, tool_args, tool_result, latency_ms)
            VALUES (?, datetime('now', 'localtime'), ?, ?, ?, ?, ?, ?)
            """,
            (session_id, role, content, tool_name, args_str, tool_result, latency_ms)
        )

    def get_session_turns(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve all turns for a specific session."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, role, content, tool_name, tool_args, tool_result, latency_ms FROM turns WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        turns = []
        for row in cursor.fetchall():
            args = None
            if row["tool_args"]:
                try:
                    args = json.loads(row["tool_args"])
                except Exception:
                    args = row["tool_args"]
            turns.append({
                "timestamp": row["timestamp"],
                "role": row["role"],
                "content": row["content"],
                "tool_name": row["tool_name"],
                "tool_args": args,
                "tool_result": row["tool_result"],
                "latency_ms": row["latency_ms"]
            })
        return turns

    def search_history(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search full conversation history for queries."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.session_id, t.timestamp, t.role, t.content, t.tool_name, t.tool_result, s.mode
            FROM turns t
            JOIN sessions s ON t.session_id = s.id
            WHERE t.content LIKE ? OR t.tool_name LIKE ? OR t.tool_result LIKE ?
            ORDER BY t.id DESC LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        )
        results = []
        for row in cursor.fetchall():
            results.append({
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "role": row["role"],
                "content": row["content"],
                "tool_name": row["tool_name"],
                "tool_result": row["tool_result"],
                "mode": row["mode"]
            })
        return results

    def get_recent_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve recent session records."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.start_time, s.end_time, s.mode, s.backend, s.summary, 
                   (SELECT COUNT(*) FROM turns WHERE session_id = s.id) as turn_count
            FROM sessions s
            ORDER BY s.mtime DESC LIMIT ?
            """,
            (limit,)
        )
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row["id"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "mode": row["mode"],
                "backend": row["backend"],
                "summary": row["summary"],
                "turn_count": row["turn_count"]
            })
        return sessions

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __del__(self):
        self.close()
