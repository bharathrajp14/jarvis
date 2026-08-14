# tests/adversarial/test_dag_parallel_safety.py — DAG Concurrency, Cycle & Conflict Safety Suite
from __future__ import annotations

import threading
import time
from typing import Any, List
import pytest

from workflow.task_dag import (
    DAGNode,
    ParallelDAGExecutor,
    PersistentTaskDAG,
    detect_cycles,
    topological_order,
)


def test_dag_concurrency_wave_execution(tmp_path):
    """Verify independent nodes execute concurrently in waves."""
    storage = PersistentTaskDAG(db_path=tmp_path / "test_dag.db")
    executor = ParallelDAGExecutor(storage=storage, max_concurrency=4)

    # Topology:
    # A (root)
    # ├── B (sleep 0.1s)
    # └── C (sleep 0.1s)
    # B & C both finish before D
    # └── D (depends on B and C)
    nodes = [
        DAGNode(node_id="A", title="Root Initialization"),
        DAGNode(node_id="B", title="Process Branch B", dependencies=["A"]),
        DAGNode(node_id="C", title="Process Branch C", dependencies=["A"]),
        DAGNode(node_id="D", title="Final Aggregation", dependencies=["B", "C"]),
    ]

    active_threads = set()
    thread_lock = threading.Lock()

    def run_node(node: DAGNode) -> str:
        with thread_lock:
            active_threads.add(threading.current_thread().name)
        if node.node_id in ("B", "C"):
            time.sleep(0.1)
        return f"Completed {node.node_id}"

    t0 = time.perf_counter()
    report = executor.execute_dag(task_id="task_wave_1", goal="Test Parallel Waves", nodes=nodes, node_runner=run_node)
    duration = time.perf_counter() - t0

    assert report.success is True
    assert len(report.failed_nodes) == 0
    # If B and C ran in parallel, duration is ~0.1s rather than ~0.2s
    assert duration < 0.25, f"Expected parallel execution, took {duration:.3f}s"


def test_dag_resource_conflict_prevention(tmp_path):
    """Verify nodes with conflicting write locks are NOT executed in the same concurrent wave."""
    storage = PersistentTaskDAG(db_path=tmp_path / "test_dag_conflict.db")
    executor = ParallelDAGExecutor(storage=storage, max_concurrency=4)

    concurrent_writes = []
    lock = threading.Lock()
    active_writers = 0

    # Node 1 and Node 2 both write to the SAME resource key "workspace/shared.txt" without explicit DAG dependency
    nodes = [
        DAGNode(node_id="W1", title="Write 1", resource_keys=["workspace/shared.txt"], is_write=True),
        DAGNode(node_id="W2", title="Write 2", resource_keys=["workspace/shared.txt"], is_write=True),
    ]

    def run_node(node: DAGNode) -> str:
        nonlocal active_writers
        with lock:
            active_writers += 1
            concurrent_writes.append(active_writers)
        time.sleep(0.08)
        with lock:
            active_writers -= 1
        return "Write done"

    report = executor.execute_dag(task_id="task_conflict_1", goal="Conflict Test", nodes=nodes, node_runner=run_node)
    assert report.success is True
    # At no point should 2 writers have been active simultaneously
    assert max(concurrent_writes) == 1, f"Conflict safety violation: {concurrent_writes}"


def test_dag_cycle_detection_refusal():
    """Verify cyclic dependency graphs are detected and refused."""
    cyclic_nodes = [
        DAGNode(node_id="A", title="Node A", dependencies=["B"]),
        DAGNode(node_id="B", title="Node B", dependencies=["A"]),
    ]

    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        detect_cycles(cyclic_nodes)


def test_dag_partial_failure_propagation(tmp_path):
    """Verify failed dependencies mark downstream tasks as FAILED while letting independent branches complete."""
    storage = PersistentTaskDAG(db_path=tmp_path / "test_dag_fail.db")
    executor = ParallelDAGExecutor(storage=storage, max_concurrency=4)

    # Topology:
    # A (fails) -> B (downstream, should fail)
    # C (independent, should succeed)
    nodes = [
        DAGNode(node_id="A", title="Failing Node"),
        DAGNode(node_id="B", title="Downstream of A", dependencies=["A"]),
        DAGNode(node_id="C", title="Independent Node"),
    ]

    def run_node(node: DAGNode) -> str:
        if node.node_id == "A":
            raise RuntimeError("Database connection timeout")
        return "OK"

    report = executor.execute_dag(task_id="task_fail_1", goal="Failure Test", nodes=nodes, node_runner=run_node)
    assert report.success is False
    assert "A" in report.failed_nodes
    assert "B" in report.failed_nodes
    assert report.node_results.get("C") == "OK"


def test_dag_cancellation_propagation(tmp_path):
    """Verify cancellation token stops execution immediately."""
    storage = PersistentTaskDAG(db_path=tmp_path / "test_dag_cancel.db")
    executor = ParallelDAGExecutor(storage=storage, max_concurrency=4)
    cancel_evt = threading.Event()

    nodes = [
        DAGNode(node_id="N1", title="Task 1"),
        DAGNode(node_id="N2", title="Task 2", dependencies=["N1"]),
    ]

    def run_node(node: DAGNode) -> str:
        cancel_evt.set()
        return "Done"

    report = executor.execute_dag(
        task_id="task_cancel_1",
        goal="Cancel Test",
        nodes=nodes,
        node_runner=run_node,
        cancel_event=cancel_evt,
    )
    assert report.success is False

