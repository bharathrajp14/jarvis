# workflow/task_dag.py — Persistent Task DAG Checkpointing & Crash Resume Engine
"""
TaskDAG provides persistent task state management supporting atomic step checkpointing,
resume, rollback, and state diffing for BR JARVIS execution goals.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS.TaskDAG")


class DAGNodeState(BaseModel):
    """Execution state of an individual Task DAG node."""

    node_id: int | str
    title: str
    tool_name: str
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    result: Optional[str] = None
    executed_at: Optional[float] = None


class PersistentTaskDAG:
    """
    Durable Task DAG state manager persisting execution checkpoints to SQLite WAL storage.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or "workspace/task_dag.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite WAL database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_checkpoints (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dag_state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def checkpoint(self, task_id: str, goal: str, nodes: List[DAGNodeState], status: str = "IN_PROGRESS") -> None:
        """Save or update an atomic task execution checkpoint."""
        now = time.time()
        serialized_nodes = json.dumps([n.model_dump() for n in nodes])

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO task_checkpoints (task_id, goal, status, dag_state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status = excluded.status,
                    dag_state = excluded.dag_state,
                    updated_at = excluded.updated_at
                """,
                (task_id, goal, status, serialized_nodes, now, now),
            )
            conn.commit()
        logger.debug(f"💾 PersistentTaskDAG: Checkpointed task '{task_id}' with {len(nodes)} nodes")

    def resume(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Resume a task checkpoint from SQLite storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM task_checkpoints WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()

        if not row:
            return None

        nodes_data = json.loads(row["dag_state"])
        nodes = [DAGNodeState(**n) for n in nodes_data]

        return {
            "task_id": row["task_id"],
            "goal": row["goal"],
            "status": row["status"],
            "nodes": nodes,
            "updated_at": row["updated_at"],
        }

    def rollback_node(self, task_id: str, node_id: int | str) -> bool:
        """Rollback a specific node status back to PENDING."""
        checkpoint_data = self.resume(task_id)
        if not checkpoint_data:
            return False

        nodes: List[DAGNodeState] = checkpoint_data["nodes"]
        updated = False
        for n in nodes:
            if str(n.node_id) == str(node_id):
                n.status = "PENDING"
                n.result = None
                updated = True

        if updated:
            self.checkpoint(task_id, checkpoint_data["goal"], nodes, checkpoint_data["status"])
            logger.info(f"🔄 PersistentTaskDAG: Rolled back node '{node_id}' in task '{task_id}'")
            return True
        return False
