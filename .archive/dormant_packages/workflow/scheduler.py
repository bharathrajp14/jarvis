# workflow/scheduler.py — Time & Event Trigger Scheduler for JARVIS MK37
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger("JARVIS.TaskScheduler")


@dataclass
class ScheduledTask:
    task_id: str
    name: str
    interval_seconds: float
    next_run: float
    handler: Callable[[], Any]
    recurring: bool = True
    last_run: Optional[float] = None


class TaskScheduler:
    """Task scheduler supporting time intervals and recurring event triggers."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running: bool = False
        self._loop_task: Optional[asyncio.Task] = None
        logger.info("⚡ TaskScheduler initialized")

    def schedule_task(
        self,
        task_id: str,
        name: str,
        interval_seconds: float,
        handler: Callable[[], Any],
        recurring: bool = True,
    ) -> None:
        """Schedule a recurring or one-shot task."""
        now = time.time()
        st = ScheduledTask(
            task_id=task_id,
            name=name,
            interval_seconds=interval_seconds,
            next_run=now + interval_seconds,
            handler=handler,
            recurring=recurring,
        )
        self._tasks[task_id] = st
        logger.info(f"⏰ TaskScheduler: Scheduled '{name}' (every {interval_seconds}s)")

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    async def start(self) -> None:
        """Start the background scheduler loop."""
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the background scheduler loop."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()

    async def _scheduler_loop(self) -> None:
        """Internal background loop checking for due tasks."""
        while self._running:
            now = time.time()
            due_tasks = [t for t in self._tasks.values() if t.next_run <= now]

            for task in due_tasks:
                try:
                    logger.info(f"⚡ TaskScheduler executing '{task.name}'")
                    res = task.handler()
                    if asyncio.iscoroutine(res):
                        await res
                    task.last_run = now
                    if task.recurring:
                        task.next_run = now + task.interval_seconds
                    else:
                        self.cancel_task(task.task_id)
                except Exception as e:
                    logger.error(f"❌ Error executing scheduled task '{task.name}': {e}")

            await asyncio.sleep(1.0)


_global_task_scheduler: Optional[TaskScheduler] = None


def get_task_scheduler() -> TaskScheduler:
    global _global_task_scheduler
    if _global_task_scheduler is None:
        _global_task_scheduler = TaskScheduler()
    return _global_task_scheduler
