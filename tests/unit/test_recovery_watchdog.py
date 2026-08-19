"""Unit tests for Crash Recovery Watchdog."""

from __future__ import annotations

import pytest

from brjarvis.agent.recovery_watchdog import TaskRecoveryWatchdog
from brjarvis.agent.task_state import TaskStateManager, TaskStatus


@pytest.mark.unit
def test_watchdog_inspect_and_recover(tmp_path):
    """Verify watchdog detects and handles interrupted tasks on recovery scan."""
    db_file = tmp_path / "test_recovery.db"
    mgr = TaskStateManager(db_path=db_file)

    task = mgr.create_task(goal="Unfinished long-running simulation")
    task.status = TaskStatus.RUNNING
    mgr.save_task(task)

    watchdog = TaskRecoveryWatchdog(task_state_mgr=mgr)
    recovery_report = watchdog.inspect_and_recover()

    assert recovery_report["recovered_count"] == 1
    assert mgr.get_task(task.task_id).status in (TaskStatus.FAILED, TaskStatus.PAUSED, TaskStatus.RECOVERING)
