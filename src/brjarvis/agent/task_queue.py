# agent/task_queue.py — Multi-Threaded Task Queue with Strict State Machine
"""
High-performance task queue with parallel execution support.
- Concurrent goal execution (multiple tasks at once)
- Strict state machine transitions (QUEUED -> RUNNING -> CANCELLING -> CANCELLED/SUCCEEDED/FAILED/TIMED_OUT)
- Immutable terminal states
- Cooperative cancellation tokens
- Thread-safe lifecycle tracking
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Cache one AgentExecutor per worker thread
_executor_thread_local = threading.local()

logger = logging.getLogger("JARVIS.TaskQueue")


class TaskStatus(str, Enum):
    PENDING    = "pending"
    QUEUED     = "queued"
    RUNNING    = "running"
    CANCELLING = "cancelling"
    COMPLETED  = "completed"
    SUCCEEDED  = "succeeded"
    FAILED     = "failed"
    CANCELLED  = "cancelled"
    TIMED_OUT  = "timed_out"
    PAUSED     = "paused"


class TaskPriority(int, Enum):
    LOW    = 3
    NORMAL = 2
    HIGH   = 1


@dataclass(order=True)
class Task:
    priority:    int
    created_at:  float              = field(compare=False)
    task_id:     str                = field(compare=False)
    goal:        str                = field(compare=False)
    status:      TaskStatus         = field(compare=False, default=TaskStatus.PENDING)
    result:      Any                = field(compare=False, default=None)
    error:       str                = field(compare=False, default="")
    speak:       Any                = field(compare=False, default=None)
    on_complete: Any                = field(compare=False, default=None)
    cancel_flag: threading.Event    = field(compare=False, default_factory=threading.Event)
    started_at:  float              = field(compare=False, default=0.0)
    finished_at: float              = field(compare=False, default=0.0)
    timeout_s:   float              = field(compare=False, default=300.0)
    timeout_requested: bool         = field(compare=False, default=False)
    _is_terminal: bool              = field(compare=False, default=False)


class TaskQueue:
    """
    Multi-threaded task queue with parallel execution and strict state transitions.
    """

    def __init__(self, max_concurrent: int | None = None, max_history: int = 100):
        cpus = os.cpu_count() or 4
        self._max = max_concurrent or min(max(3, cpus), 8)
        self._max_history = max_history

        self._queue:    List[Task]          = []
        self._lock:     threading.Lock      = threading.Lock()
        self._cond:     threading.Condition = threading.Condition(self._lock)
        self._tasks:    Dict[str, Task]     = {}
        self._running:  bool                = False
        self._paused:   bool                = False
        self._workers:  List[threading.Thread] = []
        self._active:   int                 = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._paused = False
        for i in range(self._max):
            t = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"AgentWorker-{i+1}"
            )
            t.start()
            self._workers.append(t)
        logger.info("✅ TaskQueue started with %d workers", self._max)

    def stop(self, grace_period: float = 5.0) -> None:
        """Request cancellation, wake workers, and wait a bounded time for acknowledgement."""
        with self._cond:
            self._running = False
            now = time.time()
            for task in self._tasks.values():
                if task.status in (TaskStatus.PENDING, TaskStatus.QUEUED):
                    task.cancel_flag.set()
                    task.status = TaskStatus.CANCELLED
                    task.finished_at = now
                    task._is_terminal = True
                elif task.status == TaskStatus.RUNNING:
                    task.cancel_flag.set()
                    task.status = TaskStatus.CANCELLING
            self._cond.notify_all()
        deadline = time.monotonic() + max(0.0, grace_period)
        for worker in list(self._workers):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            worker.join(timeout=remaining)
        alive = [worker.name for worker in self._workers if worker.is_alive()]
        if alive:
            logger.warning("TaskQueue shutdown grace period expired; workers still active: %s", alive)
        else:
            self._workers.clear()

    def pause(self) -> None:
        """Pause worker processing."""
        self._paused = True
        logger.info("[TaskQueue] ⏸️ Task queue paused")

    def resume(self) -> None:
        """Resume worker processing."""
        self._paused = False
        with self._cond:
            self._cond.notify_all()
        logger.info("[TaskQueue] ▶️ Task queue resumed")

    def submit(
        self,
        goal:        str,
        priority:    TaskPriority = TaskPriority.NORMAL,
        speak:       Callable | None = None,
        on_complete: Callable | None = None,
        timeout_s:   float = 300.0,
    ) -> str:
        """Submit a goal for execution. Returns task ID immediately."""
        task_id = uuid.uuid4().hex[:8]
        task = Task(
            priority    = priority.value if hasattr(priority, "value") else int(priority),
            created_at  = time.time(),
            task_id     = task_id,
            goal        = goal,
            speak       = speak,
            on_complete = on_complete,
            status      = TaskStatus.PENDING,
            timeout_s   = timeout_s,
        )

        with self._cond:
            self._queue.append(task)
            self._queue.sort(key=lambda t: (t.priority, t.created_at))
            self._tasks[task_id] = task
            self._prune_history()
            self._cond.notify()

        logger.info("📥 Queued [%s]: %s", task_id, goal[:60])
        return task_id

    def submit_many(
        self,
        goals:       List[str],
        priority:    TaskPriority = TaskPriority.NORMAL,
        speak:       Callable | None = None,
    ) -> List[str]:
        return [self.submit(goal, priority, speak) for goal in goals]

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or running task safely."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task._is_terminal or task.status in (TaskStatus.COMPLETED, TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMED_OUT):
                return False

            # Pending work terminates immediately; running work remains
            # CANCELLING until the worker acknowledges the cooperative token.
            task.cancel_flag.set()
            if task.status in (TaskStatus.PENDING, TaskStatus.QUEUED):
                task.status = TaskStatus.CANCELLED
                task.finished_at = time.time()
                task._is_terminal = True
                try:
                    self._queue.remove(task)
                except ValueError:
                    pass
            else:
                task.status = TaskStatus.CANCELLING

        return True


    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            duration = ""
            if task.started_at:
                end = task.finished_at or time.time()
                duration = f"{end - task.started_at:.1f}s"
            return {
                "task_id":  task.task_id,
                "goal":     task.goal,
                "status":   task.status.value,
                "result":   task.result,
                "error":    task.error,
                "duration": duration,
            }

    def get_all_statuses(self) -> List[Dict[str, Any]]:
        with self._lock:
            statuses = []
            for task in self._tasks.values():
                statuses.append({
                    "task_id": task.task_id,
                    "goal":    task.goal[:50],
                    "status":  task.status.value,
                    "result":  (str(task.result) or "")[:80] if task.result else "",
                })
            return statuses

    def _prune_history(self) -> None:
        if len(self._tasks) <= self._max_history:
            return

        finished_ids = [
            tid for tid, t in self._tasks.items()
            if t._is_terminal or t.status in (TaskStatus.COMPLETED, TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMED_OUT)
        ]

        overflow = len(self._tasks) - self._max_history
        for tid in finished_ids[:overflow]:
            self._tasks.pop(tid, None)

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._queue if t.status in (TaskStatus.PENDING, TaskStatus.QUEUED))

    def active_count(self) -> int:
        with self._lock:
            return self._active

    def wait_for(self, task_id: str, timeout: float = 300) -> Optional[Dict[str, Any]]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_status(task_id)
            if status and status["status"] in ("completed", "succeeded", "failed", "cancelled", "timed_out"):
                return status
            time.sleep(0.3)
        return self.get_status(task_id)

    def _worker_loop(self) -> None:
        while self._running:
            task = None
            with self._cond:
                while self._running and (self._paused or not self._can_pick()):
                    self._cond.wait(timeout=0.5)
                if self._running and not self._paused:
                    task = self._next_task()
                    if task:
                        task.status = TaskStatus.RUNNING
                        task.started_at = time.time()
                        self._active += 1
                        try:
                            self._queue.remove(task)
                        except ValueError:
                            pass

            if task:
                self._run_task(task)

    def _can_pick(self) -> bool:
        return (
            self._active < self._max and
            any(t.status in (TaskStatus.PENDING, TaskStatus.QUEUED) and not t.cancel_flag.is_set()
                for t in self._queue)
        )

    def _next_task(self) -> Optional[Task]:
        for task in self._queue:
            if task.status in (TaskStatus.PENDING, TaskStatus.QUEUED) and not task.cancel_flag.is_set():
                return task
        return None

    def _run_task(self, task: Task) -> None:
        logger.info("▶️ Running [%s]: %s", task.task_id, task.goal[:60])
        deadline_timer: Optional[threading.Timer] = None
        try:
            from brjarvis.agent.executor import AgentExecutor
            if not hasattr(_executor_thread_local, "executor"):
                _executor_thread_local.executor = AgentExecutor()
            executor = _executor_thread_local.executor

            if task.timeout_s > 0:
                deadline_timer = threading.Timer(task.timeout_s, self._request_timeout, args=(task,))
                deadline_timer.daemon = True
                deadline_timer.start()

            result = executor.execute(
                goal        = task.goal,
                speak       = task.speak,
                cancel_flag = task.cancel_flag,
            )

            with self._lock:
                task.finished_at = time.time()
                task._is_terminal = True
                if task.timeout_requested:
                    task.status = TaskStatus.TIMED_OUT
                    task.error = task.error or f"Task deadline of {task.timeout_s:.1f}s exceeded."
                elif task.cancel_flag.is_set():
                    task.status = TaskStatus.CANCELLED
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                self._active = max(0, self._active - 1)

            if task.on_complete and not task.cancel_flag.is_set():
                try:
                    task.on_complete(task.task_id, result)
                except Exception as e:
                    logger.warning("on_complete callback error for task %s: %s", task.task_id, e)

            dur = task.finished_at - task.started_at if task.finished_at else 0
            logger.info("✅ [%s] Completed in %.1fs", task.task_id, dur)

        except Exception as e:
            with self._lock:
                task.finished_at = time.time()
                task._is_terminal = True
                if task.timeout_requested:
                    task.status = TaskStatus.TIMED_OUT
                    task.error = task.error or f"Task deadline of {task.timeout_s:.1f}s exceeded."
                elif task.cancel_flag.is_set():
                    task.status = TaskStatus.CANCELLED
                else:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                self._active = max(0, self._active - 1)
            logger.error("❌ [%s] Failed: %s", task.task_id, e, exc_info=True)

        finally:
            if deadline_timer is not None:
                deadline_timer.cancel()

        with self._cond:
            self._cond.notify_all()

    def _request_timeout(self, task: Task) -> None:
        """Request cooperative cancellation when a running task exceeds its deadline."""
        with self._lock:
            if task._is_terminal or task.status != TaskStatus.RUNNING:
                return
            task.timeout_requested = True
            task.cancel_flag.set()
            task.status = TaskStatus.CANCELLING
            task.error = f"Task deadline of {task.timeout_s:.1f}s exceeded; awaiting worker acknowledgement."
        logger.warning("⏱️ [%s] Deadline exceeded; cancellation requested", task.task_id)


_queue      = TaskQueue()
_started    = False
_start_lock = threading.Lock()


def get_queue() -> TaskQueue:
    global _started
    with _start_lock:
        if not _started:
            _queue.start()
            _started = True
    return _queue
