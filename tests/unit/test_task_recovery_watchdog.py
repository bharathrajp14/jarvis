# tests/unit/test_task_recovery_watchdog.py — Unit Tests for Crash Recovery Watchdog
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from memory.canonical_db import CanonicalDatabaseManager
from agent.task_state import TaskStateManager, TaskStatus
from agent.recovery_watchdog import TaskRecoveryWatchdog


def test_watchdog_recovers_interrupted_tasks():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test_recovery.db"
        db = CanonicalDatabaseManager(db_path=db_path)
        mgr = TaskStateManager(db_manager=db)

        # Create a task left in RUNNING state with a checkpoint
        t1 = mgr.create_task("Interrupted task with checkpoint")
        t1.status = TaskStatus.RUNNING
        mgr.save_task(t1)
        mgr.create_checkpoint(t1.task_id, step_index=2)

        # Create a task left in RUNNING state without checkpoint
        t2 = mgr.create_task("Interrupted task without checkpoint")
        t2.status = TaskStatus.RUNNING
        mgr.save_task(t2)

        watchdog = TaskRecoveryWatchdog(task_state_mgr=mgr)
        report = watchdog.inspect_and_recover()

        assert report["status"] == "recovered"
        assert report["recovered_count"] == 2

        t1_recovered = mgr.get_task(t1.task_id)
        assert t1_recovered.status == TaskStatus.PAUSED
        assert "Recovered from unplanned shutdown" in t1_recovered.final_report

        t2_recovered = mgr.get_task(t2.task_id)
        assert t2_recovered.status == TaskStatus.FAILED
        assert "interrupted during execution before initial checkpoint" in t2_recovered.final_report
