# agent/task_scheduler.py — Autonomous Task DAG Scheduler
"""
TaskScheduler manages asynchronous DAG task queues and worker dispatches,
decoupling goal planning from orchestrator execution.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from workflow.task_dag import DAGNodeState, PersistentTaskDAG

logger = logging.getLogger("JARVIS.TaskScheduler")


class TaskScheduler:
    """
    Asynchronous task scheduler dispatching DAG execution nodes across worker pools.
    """

    def __init__(self, dag_store: Optional[PersistentTaskDAG] = None):
        self.dag_store = dag_store or PersistentTaskDAG()
        self.running_tasks: Dict[str, asyncio.Task] = {}

    def schedule_dag(self, task_id: str, goal: str, nodes: List[DAGNodeState]) -> None:
        """
        Schedule a set of DAG nodes for execution and persist initial checkpoint.
        """
        self.dag_store.checkpoint(task_id, goal, nodes, status="IN_PROGRESS")
        logger.info(f"📅 TaskScheduler: Scheduled DAG '{task_id}' with {len(nodes)} tasks")

    async def execute_next_pending_node(
        self, task_id: str, executor_func: Callable[[DAGNodeState], Any]
    ) -> Optional[DAGNodeState]:
        """
        Fetch the next pending node in the DAG, execute it via executor_func, and update checkpoint.
        """
        checkpoint_data = self.dag_store.resume(task_id)
        if not checkpoint_data:
            return None

        nodes: List[DAGNodeState] = checkpoint_data["nodes"]
        pending_node = next((n for n in nodes if n.status == "PENDING"), None)

        if not pending_node:
            logger.info(f"✅ TaskScheduler: All nodes completed for DAG '{task_id}'")
            self.dag_store.checkpoint(task_id, checkpoint_data["goal"], nodes, status="COMPLETED")
            return None

        # Execute node
        pending_node.status = "RUNNING"
        self.dag_store.checkpoint(task_id, checkpoint_data["goal"], nodes, status="IN_PROGRESS")

        try:
            res = executor_func(pending_node)
            if asyncio.iscoroutine(res):
                res = await res

            pending_node.status = "COMPLETED"
            pending_node.result = str(res)
            pending_node.executed_at = time.time()
        except Exception as e:
            logger.error(f"❌ TaskScheduler: Execution failed on node '{pending_node.title}': {e}")
            pending_node.status = "FAILED"
            pending_node.result = f"Error: {e}"

        self.dag_store.checkpoint(task_id, checkpoint_data["goal"], nodes, status="IN_PROGRESS")
        return pending_node
