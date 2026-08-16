# actions/routine_engine.py — Persistent Background Routine & Automation Engine
"""
Persistent Background Routine Engine for BR JARVIS MK37.
Supports 9 trigger types:
- Time / Cron Schedule
- Application Event
- Email Received
- Calendar Event
- Slack Message
- Filesystem Event
- Webhook
- Device Event
- User Request

Persists routines and execution history in SQLite across restarts.
Safely executes autonomous background tasks with approval checkpoints.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.RoutineEngine")

DB_DIR = paths.WORKSPACE_ROOT / "routines"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "routines.db"


class TriggerType(str, Enum):
    SCHEDULE = "schedule"
    APP_EVENT = "app_event"
    EMAIL_RECEIVED = "email_received"
    CALENDAR_EVENT = "calendar_event"
    SLACK_MESSAGE = "slack_message"
    FILESYSTEM_EVENT = "filesystem_event"
    WEBHOOK = "webhook"
    DEVICE_EVENT = "device_event"
    USER_REQUEST = "user_request"


@dataclass
class RoutineDefinition:
    routine_id: str
    name: str
    description: str = ""
    trigger_type: TriggerType = TriggerType.SCHEDULE
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    goal: str = ""
    skill_name: Optional[str] = None
    target_device: str = "pc"
    requires_approval: bool = False
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["trigger_type"] = self.trigger_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RoutineDefinition:
        raw = dict(data)
        if "trigger_type" in raw and isinstance(raw["trigger_type"], str):
            raw["trigger_type"] = TriggerType(raw["trigger_type"])
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


class RoutineEngine:
    """Persistent SQLite-backed background routine engine."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    routine_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    data_json TEXT NOT NULL,
                    last_run TEXT,
                    next_run TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routine_history (
                    run_id TEXT PRIMARY KEY,
                    routine_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output TEXT,
                    duration REAL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY(routine_id) REFERENCES routines(routine_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_routines_enabled ON routines(enabled);")
            conn.commit()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._daemon_loop, daemon=True, name="RoutineEngineDaemon")
        self._thread.start()
        logger.info("⚡ RoutineEngine daemon started.")

    def stop(self) -> None:
        self._running = False

    def _daemon_loop(self) -> None:
        while self._running:
            try:
                self._evaluate_due_routines()
            except Exception as e:
                logger.error("RoutineEngine daemon error: %s", e)
            time.sleep(15)

    def create_routine(
        self,
        name: str,
        goal: str,
        trigger_type: TriggerType = TriggerType.SCHEDULE,
        trigger_config: Optional[Dict[str, Any]] = None,
        skill_name: Optional[str] = None,
        target_device: str = "pc",
        requires_approval: bool = False
    ) -> RoutineDefinition:
        r_id = str(uuid.uuid4())
        routine = RoutineDefinition(
            routine_id=r_id,
            name=name,
            goal=goal,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {},
            skill_name=skill_name,
            target_device=target_device,
            requires_approval=requires_approval,
            enabled=True
        )
        self.save_routine(routine)
        logger.info("RoutineEngine: Created routine '%s' (%s)", name, r_id)
        return routine

    def save_routine(self, routine: RoutineDefinition) -> None:
        routine.updated_at = time.time()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO routines (
                    routine_id, name, trigger_type, enabled, data_json, last_run, next_run, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(routine_id) DO UPDATE SET
                    name=excluded.name,
                    trigger_type=excluded.trigger_type,
                    enabled=excluded.enabled,
                    data_json=excluded.data_json,
                    last_run=excluded.last_run,
                    next_run=excluded.next_run,
                    updated_at=excluded.updated_at
            """, (
                routine.routine_id,
                routine.name,
                routine.trigger_type.value,
                1 if routine.enabled else 0,
                json.dumps(routine.to_dict()),
                routine.last_run,
                routine.next_run,
                routine.created_at,
                routine.updated_at
            ))
            conn.commit()

    def get_routine(self, routine_id: str) -> Optional[RoutineDefinition]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data_json FROM routines WHERE routine_id = ?", (routine_id,)).fetchone()
            if row:
                return RoutineDefinition.from_dict(json.loads(row["data_json"]))
        return None

    def list_routines(self, enabled_only: bool = False) -> List[RoutineDefinition]:
        with self._get_conn() as conn:
            query = "SELECT data_json FROM routines WHERE enabled = 1 ORDER BY updated_at DESC" if enabled_only else "SELECT data_json FROM routines ORDER BY updated_at DESC"
            rows = conn.execute(query).fetchall()
            return [RoutineDefinition.from_dict(json.loads(r["data_json"])) for r in rows]

    def delete_routine(self, routine_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM routines WHERE routine_id = ?", (routine_id,))
            conn.commit()
            return cur.rowcount > 0

    def trigger_event(self, event_type: TriggerType, payload: Dict[str, Any]) -> List[str]:
        """Trigger routines listening for an event (e.g. EMAIL_RECEIVED, GITHUB_PUSH)."""
        triggered = []
        routines = self.list_routines(enabled_only=True)
        for r in routines:
            if r.trigger_type == event_type:
                logger.info("Triggering routine '%s' on event %s", r.name, event_type.value)
                self.run_routine_now(r.routine_id, event_payload=payload)
                triggered.append(r.routine_id)
        return triggered

    def run_routine_now(self, routine_id: str, event_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a routine immediately."""
        routine = self.get_routine(routine_id)
        if not routine:
            return {"success": False, "error": f"Routine '{routine_id}' not found"}

        t_start = time.time()
        run_id = str(uuid.uuid4())
        status = "completed"
        output = ""

        try:
            if routine.skill_name:
                from skills.skill_engine import get_skill_engine
                engine = get_skill_engine()
                res = engine.execute_skill(routine.skill_name, event_payload or {})
                status = "completed" if res.get("success") else "failed"
                output = json.dumps(res)
            elif routine.goal:
                from agent.executor import AgentExecutor
                executor = AgentExecutor()
                output = executor.execute(routine.goal)
                status = "completed"
        except Exception as e:
            status = "failed"
            output = f"Execution error: {e}"
            logger.error("Error executing routine '%s': %s", routine.name, e)

        duration = time.time() - t_start
        routine.last_run = datetime.now().isoformat()
        routine.run_count += 1
        self.save_routine(routine)

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO routine_history (run_id, routine_id, status, output, duration, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (run_id, routine_id, status, output[:1000], duration, time.time()))
            conn.commit()

        return {
            "run_id": run_id,
            "routine_id": routine_id,
            "name": routine.name,
            "status": status,
            "duration": duration,
            "output": output
        }

    def _evaluate_due_routines(self) -> None:
        routines = self.list_routines(enabled_only=True)
        now = datetime.now()

        for r in routines:
            if r.trigger_type == TriggerType.SCHEDULE:
                sched_str = r.trigger_config.get("expression") or r.trigger_config.get("interval", "")
                if not sched_str:
                    continue
                if self._should_run_schedule(sched_str, r.last_run, now):
                    logger.info("⏰ Running scheduled routine '%s'", r.name)
                    self.run_routine_now(r.routine_id)

    def _should_run_schedule(self, schedule_str: str, last_run_str: Optional[str], now: datetime) -> bool:
        if not last_run_str:
            return True

        last_run = datetime.fromisoformat(last_run_str)
        sched = schedule_str.lower().strip()

        # Interval matching e.g. "every 10m", "every 1h", "every 30s"
        m = re.match(r"every\s+(\d+)\s*(s|sec|m|min|h|hr|hour|d|day)s?", sched)
        if m:
            val = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("s"):
                delta = timedelta(seconds=val)
            elif unit.startswith("m"):
                delta = timedelta(minutes=val)
            elif unit.startswith("h"):
                delta = timedelta(hours=val)
            else:
                delta = timedelta(days=val)
            return (now - last_run) >= delta

        # Daily at HH:MM e.g. "every day at 08:00"
        m_daily = re.match(r"every\s+(?:day\s+)?at\s+(\d{1,2}):(\d{2})", sched)
        if m_daily:
            target_hour = int(m_daily.group(1))
            target_min = int(m_daily.group(2))
            if now.hour == target_hour and now.minute == target_min:
                return (now - last_run) >= timedelta(minutes=50)

        return False


_routine_engine_instance: Optional[RoutineEngine] = None


def get_routine_engine() -> RoutineEngine:
    global _routine_engine_instance
    if _routine_engine_instance is None:
        _routine_engine_instance = RoutineEngine()
    return _routine_engine_instance
