# tests/unit/test_canonical_db_wal.py — Unit Tests for Canonical DB and Task State WAL
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from memory.canonical_db import CanonicalDatabaseManager
from agent.task_state import TaskStateManager, TaskStatus


def test_canonical_db_tables_creation():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test_canonical.db"
        db = CanonicalDatabaseManager(db_path=db_path)
        with db.get_connection() as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            assert "tasks" in tables
            assert "task_steps" in tables
            assert "checkpoints" in tables
            assert "persistent_memories" in tables
            assert "contacts" in tables
            assert "routines" in tables


def test_task_state_manager_wal_lifecycle():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test_canonical.db"
        db = CanonicalDatabaseManager(db_path=db_path)
        mgr = TaskStateManager(db_manager=db)

        # 1. Create task
        task = mgr.create_task("Test multi-device workflow", active_devices=["pc", "android"])
        assert task.status == TaskStatus.CREATED
        assert task.goal == "Test multi-device workflow"

        # 2. Record step WAL
        step_id = mgr.record_step_wal(
            task_id=task.task_id,
            step_index=1,
            capability="web_search",
            parameters={"query": "quantum computing"},
            status="completed",
            result={"status": "found 10 articles"}
        )
        assert step_id.startswith(f"{task.task_id}_s1")

        # 3. Create Checkpoint
        chk_id = mgr.create_checkpoint(task.task_id, step_index=1)
        assert chk_id.startswith(f"chk_{task.task_id}_1")

        # 4. Request Approval
        appr = mgr.request_approval(
            task_id=task.task_id,
            action_id="step_2",
            description="Delete obsolete cache",
            risk_level="high"
        )
        t_paused = mgr.get_task(task.task_id)
        assert t_paused.status == TaskStatus.WAITING_FOR_APPROVAL
        assert t_paused.approval_request.status == "pending"

        # 5. Resolve Approval
        t_res = mgr.resolve_approval(task.task_id, appr.request_id, approved=True)
        assert t_res.status == TaskStatus.RUNNING
        assert t_res.approval_request.status == "approved"
