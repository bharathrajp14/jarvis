# tests/unit/test_cross_task_isolation.py — Task Identity, Isolation & Contamination Prevention Suite
"""
BR JARVIS MK40.2 Task Isolation Suite.
Directives 5 & 6:
- Every task must carry: task_id, session_id, request_id, step_id.
- Test that results cannot leak between Task A, Task B, and Task C.
- Reject wrong task_id, wrong step_id, stale execution_id.
- Add explicit cross-task contamination tests.
"""
from __future__ import annotations

import concurrent.futures
import time
import uuid
from typing import Dict, List
import pytest

from brjarvis.core.execution.trace import ExecutionTrace
from brjarvis.core.execution.types import ExecutionStatus
from brjarvis.memory.working import WorkingMemory
from brjarvis.tools.tool_runtime import ToolResult, ToolExecutionStatus


class TestCrossTaskIsolation:
    """Validate task identity propagation and contamination prevention."""

    def test_execution_trace_task_identity_binding(self):
        """Verify each execution trace strictly binds and retains its task identity."""
        task_a_id = f"task_{uuid.uuid4().hex[:8]}"
        task_b_id = f"task_{uuid.uuid4().hex[:8]}"

        trace_a = ExecutionTrace(task_id=task_a_id, goal="Task A: Generate Financial Summary")
        trace_b = ExecutionTrace(task_id=task_b_id, goal="Task B: Optimize System Memory")

        assert trace_a.task_id == task_a_id
        assert trace_b.task_id == task_b_id
        assert trace_a.task_id != trace_b.task_id

        trace_a.add_event("STEP", "Step 1: file_read finances.xlsx", {"path": "finances.xlsx", "duration_ms": 10.0})
        trace_b.add_event("STEP", "Step 1: system_optimize RAM", {"level": "high", "duration_ms": 25.0})

        dict_a = trace_a.to_dict()
        dict_b = trace_b.to_dict()

        assert dict_a["task_id"] == task_a_id
        assert dict_b["task_id"] == task_b_id
        assert "finances" in str(dict_a["events"])
        assert "finances" not in str(dict_b["events"])
        assert "system_optimize" in str(dict_b["events"])
        assert "system_optimize" not in str(dict_a["events"])

    def test_tool_result_task_and_step_identity_validation(self):
        """Verify tool results carry correct task_id and step_id."""
        task_id = "task_abc_123"
        step_id = "step_xyz_001"

        res = ToolResult(
            tool_name="git_repo_tool",
            task_id=task_id,
            step_id=step_id,
            status=ToolExecutionStatus.SUCCESS,
            data={"branch": "main", "clean": True},
        )

        assert res.task_id == task_id
        assert res.step_id == step_id

        # Mismatched check: ensure consumer can reject mismatched task result
        def validate_task_result(expected_task: str, expected_step: str, result: ToolResult) -> bool:
            return result.task_id == expected_task and result.step_id == expected_step

        assert validate_task_result(task_id, step_id, res) is True
        assert validate_task_result("wrong_task_id", step_id, res) is False
        assert validate_task_result(task_id, "wrong_step_id", res) is False

    def test_concurrent_working_memory_isolation(self):
        """Verify concurrent task execution does not cross-pollinate working memories."""
        results: Dict[int, List[str]] = {}
        import threading
        res_lock = threading.Lock()

        def worker(worker_id: int):
            wm = WorkingMemory()
            wm.add("system", f"System instructions for [WORKER_{worker_id}_TAG]")
            wm.add("user", f"User query from [WORKER_{worker_id}_TAG]")
            wm.add("assistant", f"Response to [WORKER_{worker_id}_TAG]")

            messages = wm.get()
            with res_lock:
                results[worker_id] = [m["content"] for m in messages]

        concurrency = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(worker, i) for i in range(concurrency)]
            concurrent.futures.wait(futures)

        assert len(results) == concurrency
        for worker_id, msgs in results.items():
            combined = " ".join(msgs)
            assert f"[worker_{worker_id}_tag]" in combined.lower()
            # Ensure no content from other workers leaked into this worker's memory
            for other_id in range(concurrency):
                if other_id != worker_id:
                    assert f"[worker_{other_id}_tag]" not in combined.lower(), f"Contamination: Worker {worker_id} has data from Worker {other_id}"


