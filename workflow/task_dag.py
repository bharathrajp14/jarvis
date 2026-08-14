from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence
from pathlib import Path

logger = logging.getLogger("JARVIS.TaskDAG")


# ── BUG-016 FIX: DAG Cycle Detection ──────────────────────────────────────────

def detect_cycles(nodes: Sequence["DAGNode"]) -> None:
    """
    Validate that the given DAG nodes contain no cyclic dependencies.

    Uses Kahn's topological sort (BFS). If all nodes cannot be processed,
    a cycle exists among the remaining nodes.

    Raises:
        ValueError: If a cycle is detected, with a message identifying the cycle nodes.
    """
    all_ids = {n.node_id for n in nodes}
    in_degree: dict[str, int] = {n.node_id: 0 for n in nodes}
    adj: dict[str, list[str]] = {n.node_id: [] for n in nodes}

    for node in nodes:
        for dep in node.dependencies:
            if dep not in all_ids:
                continue
            adj[dep].append(node.node_id)
            in_degree[node.node_id] += 1

    from collections import deque
    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    processed = 0

    while queue:
        nid = queue.popleft()
        processed += 1
        for neighbour in adj.get(nid, []):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if processed < len(all_ids):
        cycle_nodes = [nid for nid, deg in in_degree.items() if deg > 0]
        raise ValueError(
            f"[TaskDAG] Cyclic dependency detected! Nodes involved: {cycle_nodes}. "
            "Fix your task graph before execution."
        )


def topological_order(nodes: Sequence["DAGNode"]) -> list["DAGNode"]:
    """
    Return nodes in a valid topological execution order (dependencies first).

    Raises:
        ValueError: If cycles are detected.
    """
    detect_cycles(nodes)

    node_map = {n.node_id: n for n in nodes}
    all_ids = set(node_map)
    in_degree: dict[str, int] = {n.node_id: 0 for n in nodes}
    adj: dict[str, list[str]] = {n.node_id: [] for n in nodes}

    for node in nodes:
        for dep in node.dependencies:
            if dep not in all_ids:
                continue
            adj[dep].append(node.node_id)
            in_degree[node.node_id] += 1

    from collections import deque
    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    result: list["DAGNode"] = []

    while queue:
        nid = queue.popleft()
        result.append(node_map[nid])
        for neighbour in adj.get(nid, []):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    return result


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
        resource_keys: Optional[List[str]] = None,
        is_write: bool = False,
    ):
        self.node_id = node_id
        self.title = title
        self.status = status
        self.dependencies = dependencies or []
        self.result = result
        self.executed_at = executed_at
        self.resource_keys = resource_keys or []
        self.is_write = is_write

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "status": self.status,
            "dependencies": self.dependencies,
            "result": self.result,
            "executed_at": self.executed_at,
            "resource_keys": self.resource_keys,
            "is_write": self.is_write,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DAGNode:
        return cls(
            node_id=data["node_id"],
            title=data.get("title", ""),
            status=data.get("status", "PENDING"),
            dependencies=data.get("dependencies", []),
            result=data.get("result"),
            executed_at=data.get("executed_at"),
            resource_keys=data.get("resource_keys", []),
            is_write=data.get("is_write", False),
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
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
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
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
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
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
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


@dataclass
class DAGExecutionReport:
    task_id: str
    goal: str
    success: bool
    node_results: Dict[str, Any]
    failed_nodes: List[str]
    duration_sec: float


class ParallelDAGExecutor:
    """
    Dependency-aware parallel executor for workflow Task DAGs.
    Executes independent nodes concurrently in waves, respecting dependency constraints,
    atomic SQLite checkpoints, and instant cancellation.
    """

    def __init__(self, storage: Optional[PersistentTaskDAG] = None, max_concurrency: int = 4):
        self.storage = storage or PersistentTaskDAG()
        self.max_concurrency = max_concurrency

    def execute_dag(
        self,
        task_id: str,
        goal: str,
        nodes: List[DAGNode],
        node_runner: Callable[[DAGNode], Any],
        cancel_event: Optional[Any] = None,
    ) -> DAGExecutionReport:
        import concurrent.futures
        import time

        detect_cycles(nodes)
        t_start = time.monotonic()

        node_map = {n.node_id: n for n in nodes}
        completed_ids: set[str] = set()
        failed_ids: set[str] = set()
        results: Dict[str, Any] = {}

        self.storage.checkpoint(task_id, goal, nodes, "RUNNING")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrency) as pool:
            while len(completed_ids) + len(failed_ids) < len(nodes):
                if cancel_event and getattr(cancel_event, "is_set", lambda: False)():
                    logger.warning(f"[ParallelDAGExecutor] Execution cancelled for task {task_id}")
                    self.storage.checkpoint(task_id, goal, nodes, "CANCELLED")
                    return DAGExecutionReport(
                        task_id=task_id,
                        goal=goal,
                        success=False,
                        node_results=results,
                        failed_nodes=list(failed_ids),
                        duration_sec=time.monotonic() - t_start,
                    )

                # Identify all ready nodes: PENDING and all dependencies COMPLETED
                ready_candidates = [
                    n for n in nodes
                    if n.status == "PENDING"
                    and all(dep in completed_ids for dep in n.dependencies)
                    and not any(dep in failed_ids for dep in n.dependencies)
                ]

                if not ready_candidates:
                    # Check if remaining nodes are blocked by failures
                    remaining_pending = [n for n in nodes if n.status == "PENDING"]
                    if remaining_pending:
                        for n in remaining_pending:
                            n.status = "FAILED"
                            n.result = "Dependency failed"
                            failed_ids.add(n.node_id)
                        break
                    break

                # Form a conflict-free execution wave (Reader-Writer exclusion)
                ready_nodes: List[DAGNode] = []
                wave_write_res: set[str] = set()
                wave_read_res: set[str] = set()

                for cand in ready_candidates:
                    c_res = set(cand.resource_keys or [])
                    has_conflict = False
                    if cand.is_write:
                        if c_res.intersection(wave_write_res) or c_res.intersection(wave_read_res):
                            has_conflict = True
                    else:
                        if c_res.intersection(wave_write_res):
                            has_conflict = True

                    if not has_conflict:
                        ready_nodes.append(cand)
                        if cand.is_write:
                            wave_write_res.update(c_res)
                        else:
                            wave_read_res.update(c_res)

                # Execute wave in parallel
                for n in ready_nodes:
                    n.status = "RUNNING"

                futures = {
                    pool.submit(node_runner, n): n for n in ready_nodes
                }

                for future in concurrent.futures.as_completed(futures):
                    node = futures[future]
                    node.executed_at = time.time()
                    try:
                        res = future.result()
                        node.status = "COMPLETED"
                        node.result = str(res)
                        results[node.node_id] = res
                        completed_ids.add(node.node_id)
                    except Exception as exc:
                        logger.error(f"[ParallelDAGExecutor] Node {node.node_id} failed: {exc}")
                        node.status = "FAILED"
                        node.result = str(exc)
                        failed_ids.add(node.node_id)

                self.storage.checkpoint(task_id, goal, nodes, "RUNNING")

        overall_success = len(failed_ids) == 0
        final_status = "COMPLETED" if overall_success else "FAILED"
        self.storage.checkpoint(task_id, goal, nodes, final_status)

        return DAGExecutionReport(
            task_id=task_id,
            goal=goal,
            success=overall_success,
            node_results=results,
            failed_nodes=list(failed_ids),
            duration_sec=time.monotonic() - t_start,
        )

