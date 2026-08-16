# core/process.py — Process Supervision & Background Worker Engine for JARVIS MK37
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS.Process")


class TaskStatus(BaseModel):
    task_id: str
    name: str
    status: str = "running"  # running, completed, failed, cancelled
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    error: Optional[str] = None


class ProcessSupervisor:
    """Supervises background tasks and async processes with crash recovery."""

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task[Any]] = {}
        self._statuses: Dict[str, TaskStatus] = {}

    def spawn(
        self,
        task_id: str,
        name: str,
        coro_fn: Callable[[], Any],
        auto_restart: bool = False,
        max_restarts: int = 3,
    ) -> asyncio.Task[Any]:
        """Spawn a supervised background asyncio task."""

        async def _wrapper():
            restarts = 0
            while True:
                try:
                    self._statuses[task_id] = TaskStatus(task_id=task_id, name=name, status="running")
                    logger.info(f"⚙️ ProcessSupervisor: Started [{name}] (ID: {task_id})")
                    res = await coro_fn()
                    self._statuses[task_id].status = "completed"
                    self._statuses[task_id].end_time = time.time()
                    return res
                except asyncio.CancelledError:
                    self._statuses[task_id].status = "cancelled"
                    self._statuses[task_id].end_time = time.time()
                    logger.info(f"🛑 ProcessSupervisor: Cancelled [{name}]")
                    raise
                except Exception as e:
                    self._statuses[task_id].error = str(e)
                    self._statuses[task_id].end_time = time.time()
                    logger.error(f"❌ ProcessSupervisor: Process [{name}] crashed: {e}")
                    if auto_restart and restarts < max_restarts:
                        restarts += 1
                        backoff = 2 ** restarts
                        logger.warning(f"🔄 Restarting [{name}] in {backoff}s (Attempt {restarts}/{max_restarts})...")
                        await asyncio.sleep(backoff)
                    else:
                        self._statuses[task_id].status = "failed"
                        break

        task = asyncio.create_task(_wrapper(), name=f"jarvis-proc-{task_id}")
        self._tasks[task_id] = task
        return task

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task by ID."""
        task = self._tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def list_tasks(self) -> Dict[str, TaskStatus]:
        """Get status summary of all supervised processes."""
        return {k: v.model_copy() for k, v in self._statuses.items()}
