# tests/unit/test_parallel_dag_executor.py — Parallel DAG Task Executor Unit Tests
from __future__ import annotations

import time
import pytest
from workflow.task_dag import (
    DAGNode,
    ParallelDAGExecutor,
    detect_cycles,
    topological_order,
)


def test_topological_ordering_and_cycle_detection():
    n1 = DAGNode(node_id="n1", title="Task 1")
    n2 = DAGNode(node_id="n2", title="Task 2", dependencies=["n1"])
    n3 = DAGNode(node_id="n3", title="Task 3", dependencies=["n2"])

    ordered = topological_order([n3, n1, n2])
    assert [n.node_id for n in ordered] == ["n1", "n2", "n3"]

    # Test cycle detection
    n1.dependencies = ["n3"]
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        detect_cycles([n1, n2, n3])


def test_parallel_execution_waves(tmp_path):
    # Diamond DAG:
    #      n1 (root)
    #     /  \
    #    n2   n3 (parallel branch)
    #     \  /
    #      n4 (join)
    n1 = DAGNode(node_id="n1", title="Start")
    n2 = DAGNode(node_id="n2", title="Branch A", dependencies=["n1"])
    n3 = DAGNode(node_id="n3", title="Branch B", dependencies=["n1"])
    n4 = DAGNode(node_id="n4", title="Join", dependencies=["n2", "n3"])

    execution_order = []

    def mock_runner(node: DAGNode) -> str:
        execution_order.append(node.node_id)
        time.sleep(0.05)
        return f"Result for {node.title}"

    executor = ParallelDAGExecutor(max_concurrency=4)
    report = executor.execute_dag(
        task_id="test-task-1",
        goal="Run diamond DAG",
        nodes=[n1, n2, n3, n4],
        node_runner=mock_runner
    )

    assert report.success is True
    assert len(report.node_results) == 4
    # n1 must be first
    assert execution_order[0] == "n1"
    # n4 must be last
    assert execution_order[-1] == "n4"
    # n2 and n3 ran between n1 and n4
    assert set(execution_order[1:3]) == {"n2", "n3"}
