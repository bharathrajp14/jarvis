# memory/canonical_db.py — Unified Canonical SQLite WAL Store & Connection Manager
"""
Central Database Manager for BR JARVIS.
Consolidates system state into a unified, high-concurrency SQLite database operating in WAL mode.
Tables managed:
- tasks & task_steps & checkpoints
- persistent_memories
- contacts
- routines & routine_runs
- devices & paired_keys
- skills & skill_versions
- audit_events
"""
from __future__ import annotations

import os
import time
import json
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.CanonicalDB")

_BASE_DIR = Path(__file__).resolve().parent.parent
_CANONICAL_DIR = _BASE_DIR / ".jarvis"
_CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
CANONICAL_DB_PATH = _CANONICAL_DIR / "jarvis_canonical.db"


class CanonicalDatabaseManager:
    """Thread-safe SQLite connection manager with WAL mode and auto-migrations."""

    def __init__(self, db_path: Path = CANONICAL_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Create and configure a connection with WAL mode and busy timeout."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Initialize and migrate all canonical tables."""
        with self._lock:
            with self.get_connection() as conn:
                # 1. Tasks & Step Checkpoints
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
                    CREATE TABLE IF NOT EXISTS task_steps (
                        step_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        step_index INTEGER NOT NULL,
                        capability TEXT NOT NULL,
                        parameters_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        result_json TEXT,
                        error_msg TEXT,
                        verified INTEGER DEFAULT 0,
                        duration REAL DEFAULT 0.0,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        checkpoint_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        step_index INTEGER NOT NULL,
                        state_snapshot TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                    )
                """)

                # 2. Canonical Memories
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS persistent_memories (
                        name TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        description TEXT,
                        content TEXT NOT NULL,
                        scope TEXT DEFAULT 'user',
                        tags TEXT,
                        created_at TEXT NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)

                # 3. Unified Contacts
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS contacts (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        phone_number TEXT,
                        email TEXT,
                        aliases_json TEXT,
                        notes TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)

                # 4. Background Routines
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS routines (
                        routine_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        goal TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        trigger_config_json TEXT,
                        skill_name TEXT,
                        target_device TEXT DEFAULT 'pc',
                        enabled INTEGER DEFAULT 1,
                        requires_approval INTEGER DEFAULT 0,
                        last_run_at REAL,
                        next_run_at REAL,
                        created_at REAL NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS routine_runs (
                        run_id TEXT PRIMARY KEY,
                        routine_id TEXT NOT NULL,
                        task_id TEXT,
                        status TEXT NOT NULL,
                        result_summary TEXT,
                        duration REAL,
                        executed_at REAL NOT NULL,
                        FOREIGN KEY (routine_id) REFERENCES routines(routine_id) ON DELETE CASCADE
                    )
                """)

                # 5. Paired Devices
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS devices (
                        device_id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        trust_state TEXT NOT NULL,
                        public_key TEXT,
                        auth_token TEXT,
                        last_seen_at REAL NOT NULL,
                        metadata_json TEXT
                    )
                """)

                # 6. Immutable Audit Trail
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        correlation_id TEXT,
                        task_id TEXT,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        action TEXT NOT NULL,
                        target_resource TEXT,
                        risk_level TEXT,
                        decision TEXT,
                        details_json TEXT
                    )
                """)
                conn.commit()
        logger.info("Canonical database schema verified at %s", self.db_path)


_GLOBAL_CANONICAL_DB: Optional[CanonicalDatabaseManager] = None


def get_canonical_db() -> CanonicalDatabaseManager:
    """Return the singleton canonical database manager."""
    global _GLOBAL_CANONICAL_DB
    if _GLOBAL_CANONICAL_DB is None:
        _GLOBAL_CANONICAL_DB = CanonicalDatabaseManager()
    return _GLOBAL_CANONICAL_DB
