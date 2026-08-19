from __future__ import annotations

import time

import pytest

from brjarvis.agent.task_queue import TaskQueue


class CooperativeExecutor:
    def execute(self, goal, speak=None, cancel_flag=None):
        while cancel_flag is not None and not cancel_flag.is_set():
            time.sleep(0.005)
        time.sleep(0.03)
        return "cooperatively stopped"


def _wait_for_status(queue: TaskQueue, task_id: str, expected: set[str], timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = queue.get_status(task_id)
        if status and status["status"] in expected:
            return status
        time.sleep(0.01)
    pytest.fail(f"Task {task_id} did not reach {sorted(expected)}; last={queue.get_status(task_id)}")


@pytest.mark.unit
def test_pending_task_cancels_immediately():
    queue = TaskQueue(max_concurrent=1)
    task_id = queue.submit("pending cancellation")

    assert queue.cancel(task_id) is True
    assert queue.get_status(task_id)["status"] == "cancelled"


@pytest.mark.unit
def test_running_task_remains_cancelling_until_worker_acknowledges(monkeypatch):
    monkeypatch.setattr("brjarvis.agent.executor.AgentExecutor", CooperativeExecutor)
    queue = TaskQueue(max_concurrent=1)
    queue.start()
    task_id = queue.submit("running cancellation", timeout_s=10)
    _wait_for_status(queue, task_id, {"running"})

    assert queue.cancel(task_id) is True
    assert queue.get_status(task_id)["status"] == "cancelling"
    final = _wait_for_status(queue, task_id, {"cancelled"})

    assert final["status"] == "cancelled"
    queue.stop(grace_period=1)


@pytest.mark.unit
def test_task_deadline_requests_cancellation_and_finishes_timed_out(monkeypatch):
    monkeypatch.setattr("brjarvis.agent.executor.AgentExecutor", CooperativeExecutor)
    queue = TaskQueue(max_concurrent=1)
    queue.start()
    task_id = queue.submit("deadline", timeout_s=0.05)

    final = _wait_for_status(queue, task_id, {"timed_out"})

    assert final["status"] == "timed_out"
    assert "deadline" in final["error"].lower()
    queue.stop(grace_period=1)


@pytest.mark.unit
def test_stop_cancels_running_work_and_joins_worker(monkeypatch):
    monkeypatch.setattr("brjarvis.agent.executor.AgentExecutor", CooperativeExecutor)
    queue = TaskQueue(max_concurrent=1)
    queue.start()
    task_id = queue.submit("shutdown cancellation", timeout_s=10)
    _wait_for_status(queue, task_id, {"running"})

    queue.stop(grace_period=1)

    assert queue.get_status(task_id)["status"] == "cancelled"
    assert not queue._workers
