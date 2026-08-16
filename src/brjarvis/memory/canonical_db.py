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

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.CanonicalDB")

_CANONICAL_DIR = paths.PROJECT_ROOT / ".jarvis"
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

                # 7. Workspace Projects
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        project_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        instructions TEXT DEFAULT '',
                        settings_json TEXT DEFAULT '{}',
                        pinned INTEGER DEFAULT 0,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)

                # 8. Workspace Project Files
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS project_files (
                        file_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size INTEGER DEFAULT 0,
                        mime_type TEXT DEFAULT 'application/octet-stream',
                        file_hash TEXT DEFAULT '',
                        status TEXT DEFAULT 'READY',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                    )
                """)

                # 9. Workspace Conversations
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        project_id TEXT,
                        title TEXT NOT NULL,
                        pinned INTEGER DEFAULT 0,
                        archived INTEGER DEFAULT 0,
                        active_branch_id TEXT DEFAULT 'main',
                        summary TEXT DEFAULT '',
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE SET NULL
                    )
                """)

                # 10. Conversation Branches
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_branches (
                        branch_id TEXT NOT NULL,
                        conversation_id TEXT NOT NULL,
                        parent_message_id TEXT,
                        name TEXT NOT NULL DEFAULT 'Main Branch',
                        created_at REAL NOT NULL,
                        PRIMARY KEY (conversation_id, branch_id),
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                    )
                """)

                # 11. Conversation Messages
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        branch_id TEXT DEFAULT 'main',
                        parent_message_id TEXT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL DEFAULT '',
                        tool_calls_json TEXT DEFAULT '[]',
                        linked_task_id TEXT,
                        linked_artifacts_json TEXT DEFAULT '[]',
                        backend TEXT DEFAULT 'gemini',
                        latency_ms INTEGER DEFAULT 0,
                        created_at REAL NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                    )
                """)

                # 12. Workspace Artifacts
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS artifacts (
                        artifact_id TEXT PRIMARY KEY,
                        conversation_id TEXT,
                        task_id TEXT,
                        project_id TEXT,
                        message_id TEXT,
                        filename TEXT NOT NULL,
                        host_path TEXT NOT NULL,
                        sandbox_path TEXT,
                        mime_type TEXT DEFAULT 'application/octet-stream',
                        file_size INTEGER DEFAULT 0,
                        sha256 TEXT DEFAULT '',
                        version INTEGER DEFAULT 1,
                        provider TEXT DEFAULT 'jarvis',
                        verification_status TEXT DEFAULT 'PENDING',
                        created_at REAL NOT NULL,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE SET NULL,
                        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE SET NULL
                    )
                """)

                # 13. System & Task Notifications
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        notification_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        category TEXT DEFAULT 'ALL',
                        severity TEXT DEFAULT 'info',
                        is_read INTEGER DEFAULT 0,
                        action_link TEXT,
                        data_json TEXT DEFAULT '{}',
                        created_at REAL NOT NULL
                    )
                """)

                # 14. Indexes for optimal workspace query speed
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_project ON conversations(project_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_branch ON messages(branch_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_conv ON artifacts(conversation_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);")

                # 15. Full-Text Search (FTS5) for Instant Global Search
                try:
                    conn.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS workspace_fts USING fts5(
                            entity_type,
                            entity_id,
                            title,
                            content,
                            project_id,
                            tokenize='porter unicode61'
                        );
                    """)
                except Exception as _fts_err:
                    logger.debug("FTS5 table setup note: %s", _fts_err)

                conn.commit()
        logger.info("Canonical database schema verified at %s", self.db_path)


_GLOBAL_CANONICAL_DB: Optional[CanonicalDatabaseManager] = None


def get_canonical_db() -> CanonicalDatabaseManager:
    """Return the singleton canonical database manager."""
    global _GLOBAL_CANONICAL_DB
    if _GLOBAL_CANONICAL_DB is None:
        _GLOBAL_CANONICAL_DB = CanonicalDatabaseManager()
    return _GLOBAL_CANONICAL_DB
