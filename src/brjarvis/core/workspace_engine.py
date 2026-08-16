# core/workspace_engine.py — BR JARVIS Self-Organizing Cognitive Workspace Engine
"""
Core Cognitive Workspace Engine for BR JARVIS AI OS.
Manages BR_WORKSPACE/ root vault, project lifecycles, self-healing file organization,
smart semantic retrieval, and workspace timeline event logging.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def _get_project_root() -> Path:
    from brjarvis.core.paths import paths
    return paths.PROJECT_ROOT


class CognitiveWorkspaceEngine:
    """Master AI OS Workspace System Controller."""

    _instance = None

    ROOT_FOLDERS = [
        "Projects", "Memory", "Knowledge", "Conversations", "Documents",
        "Downloads", "Screenshots", "Images", "Audio", "Video", "Code",
        "Research", "Browser", "Automation", "Models", "Plugins", "Config",
        "Cache", "Logs", "Temporary", "Trash", "Archive", "AI_Output",
        "AI_Drafts", "Templates", "Reports", "Exports", "Database",
        "Sessions", "Timeline", "Workflows", "Assets"
    ]

    PROJECT_FOLDERS = [
        "source", "documents", "meeting_notes", "design", "architecture",
        "api", "database", "frontend", "backend", "assets", "images",
        "screenshots", "research", "references", "prompt_library",
        "generated", "exports", "build", "logs", "tests", "benchmark",
        "timeline", "versions", "memories", "tasks", "todos", "issues"
    ]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.root_dir = _get_project_root() / "BR_WORKSPACE"
        self.db_path = self.root_dir / "Database" / "workspace_core.db"
        self._ensure_workspace_structure()
        self._init_sqlite_db()
        self._initialized = True

    def _ensure_workspace_structure(self):
        """Create single root BR_WORKSPACE/ and all 32 core folders."""
        self.root_dir.mkdir(parents=True, exist_ok=True)
        for folder in self.ROOT_FOLDERS:
            (self.root_dir / folder).mkdir(exist_ok=True)

    def _init_sqlite_db(self):
        """Initialize workspace metadata and knowledge graph tables."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_files (
            file_id TEXT PRIMARY KEY,
            relative_path TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            extension TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed_at TIMESTAMP,
            project_name TEXT,
            category TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS file_semantic_metadata (
            file_id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            keywords TEXT,
            importance_score REAL DEFAULT 0.5,
            FOREIGN KEY(file_id) REFERENCES workspace_files(file_id) ON DELETE CASCADE
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_timeline (
            event_id TEXT PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            project_name TEXT,
            description TEXT NOT NULL,
            metadata_json TEXT
        )
        """)

        conn.commit()
        conn.close()

    def get_path(self, category: str) -> Path:
        """Get absolute path to a root workspace subfolder."""
        p = self.root_dir / category
        p.mkdir(parents=True, exist_ok=True)
        return p

    def create_project_workspace(self, project_name: str) -> Path:
        """Create standardized Project_Name/ workspace sub-tree."""
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", project_name)
        proj_dir = self.root_dir / "Projects" / clean_name
        proj_dir.mkdir(parents=True, exist_ok=True)

        for folder in self.PROJECT_FOLDERS:
            (proj_dir / folder).mkdir(exist_ok=True)

        self.log_timeline_event(
            event_type="PROJECT_CREATED",
            description=f"Initialized Project Workspace for '{project_name}'",
            project_name=clean_name
        )
        return proj_dir

    def log_timeline_event(self, event_type: str, description: str, project_name: str | None = None, metadata: dict | None = None):
        """Record an event in the timeline event stream."""
        import uuid
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO workspace_timeline (event_id, event_type, project_name, description, metadata_json) VALUES (?, ?, ?, ?, ?)",
            (event_id, event_type, project_name, description, json.dumps(metadata or {}))
        )
        conn.commit()
        conn.close()

    def smart_find_file(self, query: str) -> Path | None:
        """
        Smart Natural Language file retrieval.
        Finds files by keywords, topics, project name, or date without exact paths.
        """
        clean = query.lower().strip()
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        cur = conn.cursor()

        # 1. Direct filename search in database
        cur.execute("SELECT relative_path FROM workspace_files WHERE filename LIKE ? OR relative_path LIKE ? ORDER BY updated_at DESC LIMIT 1",
                    (f"%{clean}%", f"%{clean}%"))
        row = cur.fetchone()
        if row:
            conn.close()
            return self.root_dir / row[0]

        conn.close()

        # 2. File system fallback search in BR_WORKSPACE/
        keywords = [w for w in clean.split() if len(w) > 3]
        for p in self.root_dir.rglob("*"):
            if p.is_file():
                fname_low = p.name.lower()
                if any(kw in fname_low for kw in keywords):
                    return p

        return None
