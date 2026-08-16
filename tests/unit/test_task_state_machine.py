"""Unit tests for Autonomous Task State Machine & Queue."""
from __future__ import annotations

import pytest
from brjarvis.agent.task_state import TaskStateManager, TaskStatus


@pytest.mark.unit
def test_task_state_transitions(tmp_path):
    """Verify task state transitions from PENDING -> RUNNING -> COMPLETED."""
    db_file = tmp_path / "test_tasks.db"
    mgr = TaskStateManager(db_path=db_file)

    task = mgr.create_task(goal="Analyze system memory consumption")
    assert task.status == TaskStatus.PENDING

    mgr.update_status(task.task_id, TaskStatus.RUNNING)
    assert mgr.get_task(task.task_id).status == TaskStatus.RUNNING

    mgr.update_status(task.task_id, TaskStatus.COMPLETED)
    completed = mgr.get_task(task.task_id)
    assert completed.status == TaskStatus.COMPLETED
