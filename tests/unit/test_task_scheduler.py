# tests/unit/test_task_scheduler.py — Unit Tests for DAG Task Scheduler
"""
Unit tests for PersistentTaskDAG storage engine and TaskScheduler execution flow.
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
import pytest

from workflow.task_dag import DAGNode, PersistentTaskDAG
from agent.task_scheduler import TaskScheduler


def test_dagnode_serialization():
    node = DAGNode(
        node_id="task_1",
        title="Compile Source Code",
        status="PENDING",
        dependencies=["init_task"],
        result="Success",
        executed_at=1234567.89,
    )
    d = node.to_dict()
    assert d["node_id"] == "task_1"
    assert d["title"] == "Compile Source Code"
    assert d["status"] == "PENDING"
    assert d["dependencies"] == ["init_task"]
    assert d["result"] == "Success"
    assert d["executed_at"] == 1234567.89

    node2 = DAGNode.from_dict(d)
    assert node2.node_id == "task_1"
    assert node2.title == "Compile Source Code"
    assert node2.status == "PENDING"
    assert node2.dependencies == ["init_task"]
    assert node2.result == "Success"
    assert node2.executed_at == 1234567.89


def test_persistent_task_dag_checkpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "task_dags.json"
        store = PersistentTaskDAG(db_path=db_path)

        nodes = [
            DAGNode(node_id="n1", title="Init Workspace"),
            DAGNode(node_id="n2", title="Build Package", dependencies=["n1"]),
        ]

        store.checkpoint("dag_101", "Build application", nodes, "IN_PROGRESS")

        # Load fresh instance to check persistence
        store2 = PersistentTaskDAG(db_path=db_path)
        data = store2.resume("dag_101")

        assert data is not None
        assert data["goal"] == "Build application"
        assert data["status"] == "IN_PROGRESS"
        assert len(data["nodes"]) == 2
        assert data["nodes"][0].node_id == "n1"
        assert data["nodes"][1].node_id == "n2"


@pytest.mark.anyio
async def test_task_scheduler_execution_loop():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "task_dags.json"
        store = PersistentTaskDAG(db_path=db_path)
        scheduler = TaskScheduler(dag_store=store)

        nodes = [
            DAGNode(node_id="t1", title="Step 1"),
            DAGNode(node_id="t2", title="Step 2"),
        ]

        scheduler.schedule_dag("dag_abc", "Do task workflow", nodes)

        executions = []

        async def mock_executor(node: DAGNode):
            executions.append(node.title)
            return f"Ran {node.title}"

        # Run first node
        n_ran_1 = await scheduler.execute_next_pending_node("dag_abc", mock_executor)
        assert n_ran_1 is not None
        assert n_ran_1.status == "COMPLETED"
        assert n_ran_1.result == "Ran Step 1"

        # Run second node
        n_ran_2 = await scheduler.execute_next_pending_node("dag_abc", mock_executor)
        assert n_ran_2 is not None
        assert n_ran_2.status == "COMPLETED"
        assert n_ran_2.result == "Ran Step 2"

        # No more pending nodes
        n_ran_3 = await scheduler.execute_next_pending_node("dag_abc", mock_executor)
        assert n_ran_3 is None

        # Verify DAG is saved as completed
        resumed = store.resume("dag_abc")
        assert resumed["status"] == "COMPLETED"
        assert executions == ["Step 1", "Step 2"]
