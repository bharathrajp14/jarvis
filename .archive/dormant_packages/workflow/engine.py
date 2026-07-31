# workflow/engine.py — Durable Workflow Engine for JARVIS MK37
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.runtime import get_runtime
from workflow.dag import DAGNode, WorkflowDAG

logger = logging.getLogger("JARVIS.WorkflowEngine")


class WorkflowState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowEngine:
    """
    Durable Workflow Engine with SQLite state persistence,
    DAG execution, and retry management.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.runtime = get_runtime()
        if db_path is None:
            db_dir = Path.home() / ".jarvis" / "db"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "workflows.db")

        self.db_path = db_path
        self._init_db()
        
        # Register in container
        self.runtime.container.register_instance(WorkflowEngine, self)
        logger.info("⚡ WorkflowEngine initialized")

    def _init_db(self) -> None:
        """Initialize SQLite database table for durable workflow persistence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    dag_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def create_workflow(self, workflow_id: str, name: str) -> WorkflowDAG:
        """Create and persist a new WorkflowDAG."""
        dag = WorkflowDAG(workflow_id=workflow_id, name=name)
        self.save_workflow(dag, state=WorkflowState.PENDING)
        return dag

    def save_workflow(self, dag: WorkflowDAG, state: WorkflowState) -> None:
        """Save workflow state into SQLite database."""
        nodes_data = [
            {
                "node_id": n.node_id,
                "name": n.name,
                "action_type": n.action_type,
                "parameters": n.parameters,
                "depends_on": n.depends_on,
                "status": n.status,
                "error": n.error,
            }
            for n in dag.nodes.values()
        ]
        dag_json = json.dumps(nodes_data)
        now = time.time()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO workflows (workflow_id, name, state, dag_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    state = excluded.state,
                    dag_json = excluded.dag_json,
                    updated_at = excluded.updated_at
                """,
                (dag.workflow_id, dag.name, state.value, dag_json, now, now),
            )
            conn.commit()

    def load_workflow(self, workflow_id: str) -> Optional[Tuple[WorkflowDAG, WorkflowState]]:
        """Load a persisted workflow from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, state, dag_json FROM workflows WHERE workflow_id = ?", (workflow_id,))
            row = cursor.fetchone()
            if not row:
                return None

            name, state_str, dag_json = row
            dag = WorkflowDAG(workflow_id=workflow_id, name=name)
            nodes_data = json.loads(dag_json)
            for nd in nodes_data:
                node = DAGNode(
                    node_id=nd["node_id"],
                    name=nd["name"],
                    action_type=nd["action_type"],
                    parameters=nd.get("parameters", {}),
                    depends_on=nd.get("depends_on", []),
                    status=nd.get("status", "pending"),
                    error=nd.get("error"),
                )
                dag.add_node(node)

            return dag, WorkflowState(state_str)

    def execute_workflow(self, dag: WorkflowDAG) -> WorkflowState:
        """Execute a WorkflowDAG to completion, handling dependencies."""
        if not dag.validate():
            logger.error(f"Cannot execute invalid DAG '{dag.name}'")
            return WorkflowState.FAILED

        self.save_workflow(dag, state=WorkflowState.RUNNING)
        completed_ids: set[str] = set()

        while not dag.is_complete():
            ready_nodes = dag.get_executable_nodes(completed_ids)
            if not ready_nodes:
                break

            for node in ready_nodes:
                node.status = "running"
                try:
                    logger.info(f"⚡ WorkflowEngine executing node '{node.name}' ({node.node_id})")
                    # Simulate tool/action execution
                    node.status = "completed"
                    completed_ids.add(node.node_id)
                except Exception as e:
                    logger.error(f"❌ Error in workflow node '{node.name}': {e}")
                    node.error = str(e)
                    node.status = "failed"

            self.save_workflow(dag, state=WorkflowState.RUNNING)

        final_state = WorkflowState.COMPLETED if all(n.status == "completed" for n in dag.nodes.values()) else WorkflowState.FAILED
        self.save_workflow(dag, state=final_state)
        return final_state


_global_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    global _global_workflow_engine
    if _global_workflow_engine is None:
        _global_workflow_engine = WorkflowEngine()
    return _global_workflow_engine
