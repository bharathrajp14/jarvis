# actions/scheduler.py — JARVIS MK37 Intelligent Task Scheduler
"""
Natural language task scheduler for JARVIS MK37.
Allows scheduling goals (e.g. "every day at 9:00am") and running them via TaskQueue.
"""
from __future__ import annotations

import logging
import sqlite3
import time
import threading
import re
from datetime import datetime, timedelta
from pathlib import Path

from brjarvis.memory.persistent_store import get_memory_dir
from brjarvis.tools.registry import register_tool
from brjarvis.agent.task_queue import get_queue, TaskPriority

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Intelligent scheduler that checks scheduled tasks and triggers TaskQueue runs."""

    def __init__(self):
        db_dir = get_memory_dir("user")
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "scheduler.db"
        self._init_db()
        self._running = False
        self._thread = None

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule TEXT, -- "every 5m", "every day at 12:00", etc.
                    goal TEXT,
                    last_run TEXT,
                    active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _scheduler_loop(self):
        while self._running:
            try:
                self._check_and_run_tasks()
            except Exception as e:
                logger.info(f"[Scheduler] Loop warning: {e}")
            time.sleep(30)

    def _check_and_run_tasks(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, schedule, goal, last_run FROM scheduled_tasks WHERE active = 1")
            rows = cursor.fetchall()
            now = datetime.now()
            
            for row in rows:
                if self._should_run(row["schedule"], row["last_run"], now):
                    self._trigger_task(row["id"], row["goal"], now)
        finally:
            conn.close()

    def _should_run(self, schedule_str: str, last_run_str: str | None, now: datetime) -> bool:
        if not last_run_str:
            return True  # Run immediately if it has never run

        last_run = datetime.fromisoformat(last_run_str)
        sched = schedule_str.lower().strip()

        # Pattern: "every N minutes" / "every N seconds" / "every N hours"
        m = re.match(r"every\s+(\d+)\s*(s|sec|second|m|min|minute|h|hr|hour)s?", sched)
        if m:
            val = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("s"):
                delta = timedelta(seconds=val)
            elif unit.startswith("m"):
                delta = timedelta(minutes=val)
            else:
                delta = timedelta(hours=val)
            return (now - last_run) >= delta

        # Pattern: "every day at HH:MM" / "daily at HH:MM"
        m = re.match(r"(every day|daily)\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)?", sched)
        if m:
            hour = int(m.group(2))
            minute = int(m.group(3))
            ampm = m.group(4)
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            
            target_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # If it's already past target today, and last run was before target today, run it!
            if now >= target_today:
                return last_run < target_today
            
            # If target today is in future, check if last run was before yesterday's target
            target_yesterday = target_today - timedelta(days=1)
            return last_run < target_yesterday

        return False

    def _trigger_task(self, task_id: int, goal: str, now: datetime):
        logger.info(f"[Scheduler] ⏰ Triggering scheduled goal: {goal!r}")
        try:
            q = get_queue()
            q.submit(goal, priority=TaskPriority.NORMAL)
            
            # Update last run
            conn = sqlite3.connect(str(self.db_path), timeout=15.0)
            conn.execute(
                "UPDATE scheduled_tasks SET last_run = ? WHERE id = ?",
                (now.isoformat(), task_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"[Scheduler] Failed to trigger task {task_id}: {e}")

    def add(self, schedule: str, goal: str) -> int:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scheduled_tasks (schedule, goal) VALUES (?, ?)",
                (schedule, goal)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def remove(self, task_id: int) -> bool:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_all(self) -> list[dict]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, schedule, goal, last_run, active FROM scheduled_tasks")
            return [
                {
                    "id": r["id"],
                    "schedule": r["schedule"],
                    "goal": r["goal"],
                    "last_run": r["last_run"],
                    "active": bool(r["active"])
                }
                for r in cursor.fetchall()
            ]
        finally:
            conn.close()


# Singleton & Auto-start
_scheduler = TaskScheduler()
_scheduler.start()


@register_tool(
    name="scheduler",
    description="Schedule automated goals to run at intervals or specific times.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "add, remove, list"},
            "schedule": {"type": "string", "description": "Time interval, e.g. 'every 10 minutes', 'every day at 9:30am' (required for action='add')"},
            "goal": {"type": "string", "description": "Goal to execute (required for action='add')"},
            "task_id": {"type": "integer", "description": "Scheduler task ID to remove (required for action='remove')"},
        },
        "required": ["action"],
    }
)
def tool_scheduler(args: dict) -> str:
    action = args.get("action", "list").lower()
    schedule = args.get("schedule", "")
    goal = args.get("goal", "")
    task_id = args.get("task_id")

    if action == "add":
        if not schedule or not goal:
            return "ERROR: both 'schedule' and 'goal' parameters are required to add a task."
        tid = _scheduler.add(schedule, goal)
        return f"Task scheduled successfully. ID: {tid} | Run: {schedule} -> {goal!r}"

    elif action == "remove":
        if task_id is None:
            return "ERROR: 'task_id' parameter is required to remove a scheduled task."
        ok = _scheduler.remove(task_id)
        if ok:
            return f"Scheduled task ID {task_id} has been removed."
        return f"ERROR: Scheduled task ID {task_id} not found."

    else:
        tasks = _scheduler.list_all()
        if not tasks:
            return "No tasks currently scheduled."
        lines = ["Scheduled automated tasks:"]
        for t in tasks:
            status = "active" if t["active"] else "inactive"
            last = t["last_run"] or "Never"
            lines.append(f"  ● ID {t['id']}: [{t['schedule']}] {t['goal']!r} (Status: {status}, Last run: {last})")
        return "\n".join(lines)
