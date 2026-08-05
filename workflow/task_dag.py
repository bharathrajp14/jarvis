from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

class DAGNodeState(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DAGNode:
    """Execution node in a workflow Task DAG."""

    def __init__(
        self,
        node_id: str,
        title: str,
        status: str = "PENDING",
        dependencies: List[str] = None,
        result: Optional[str] = None,
        executed_at: Optional[float] = None,
    ):
        self.node_id = node_id
        self.title = title
        self.status = status
        self.dependencies = dependencies or []
        self.result = result
        self.executed_at = executed_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "status": self.status,
            "dependencies": self.dependencies,
            "result": self.result,
            "executed_at": self.executed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DAGNode:
        return cls(
            node_id=data["node_id"],
            title=data["title"],
            status=data.get("status", "PENDING"),
            dependencies=data.get("dependencies", []),
            result=data.get("result"),
            executed_at=data.get("executed_at"),
        )


class PersistentTaskDAG:
    """Persistent storage engine for scheduling and recovering workflow Task DAGs using SQLite WAL."""

    def __init__(self, db_path: Optional[Path] = None):
        import sqlite3
        from memory.persistent_store import get_memory_dir
        if db_path:
            self.db_path = Path(db_path)
        else:
            db_dir = get_memory_dir("user")
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = db_dir / "task_dags.db"
        self._init_db()

    def _init_db(self) -> None:
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dags (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dag_nodes (
                    task_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_data TEXT,
                    output_data TEXT,
                    error TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (task_id, node_id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def checkpoint(self, task_id: str, goal: str, nodes: List[Any], status: str) -> None:
        import sqlite3
        import json
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "INSERT OR REPLACE INTO task_dags (task_id, goal, status) VALUES (?, ?, ?)",
                (task_id, goal, status)
            )

            for node in nodes:
                node_id = getattr(node, "node_id", str(id(node)))
                node_status = getattr(node, "status", "PENDING")
                
                input_dict = {
                    "title": getattr(node, "title", str(node)),
                    "dependencies": getattr(node, "dependencies", []),
                    "executed_at": getattr(node, "executed_at", None),
                }
                input_data_str = json.dumps(input_dict, ensure_ascii=False)
                
                output_data = getattr(node, "result", None)
                error_msg = getattr(node, "error", None)
                if node_status == "FAILED" and not error_msg:
                    error_msg = output_data

                conn.execute(
                    """
                    INSERT OR REPLACE INTO task_dag_nodes 
                    (task_id, node_id, status, input_data, output_data, error)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (task_id, node_id, node_status, input_data_str, output_data, error_msg)
                )
            conn.commit()
        finally:
            conn.close()

    def resume(self, task_id: str) -> Optional[Dict[str, Any]]:
        import sqlite3
        import json
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT goal, status FROM task_dags WHERE task_id = ?", (task_id,))
            dag_row = cursor.fetchone()
            if not dag_row:
                return None
            
            cursor.execute(
                "SELECT node_id, status, input_data, output_data, error FROM task_dag_nodes WHERE task_id = ?",
                (task_id,)
            )
            node_rows = cursor.fetchall()
            
            nodes = []
            for row in node_rows:
                node_id = row["node_id"]
                node_status = row["status"]
                output_data = row["output_data"]
                error_msg = row["error"]
                
                try:
                    input_dict = json.loads(row["input_data"]) if row["input_data"] else {}
                except Exception:
                    input_dict = {}
                
                nodes.append(DAGNode(
                    node_id=node_id,
                    title=input_dict.get("title", node_id),
                    status=node_status,
                    dependencies=input_dict.get("dependencies", []),
                    result=output_data,
                    executed_at=input_dict.get("executed_at"),
                ))
            
            return {
                "goal": dag_row["goal"],
                "status": dag_row["status"],
                "nodes": nodes
            }
        finally:
            conn.close()
