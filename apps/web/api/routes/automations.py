# api/routes/automations.py — Automation & Background Routines Endpoints
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from brjarvis.actions.routine_engine import RoutineEngine, get_routine_engine
from brjarvis.memory.canonical_db import get_canonical_db

logger = logging.getLogger("JARVIS.API.Automations")
router = APIRouter(tags=["Automations"])


class ToggleAutomationRequest(BaseModel):
    enabled: bool


@router.get("/api/automations")
async def list_automations():
    """List all scheduled background automations and routines."""
    engine = get_routine_engine()
    routines = engine.list_routines()
    return {"total": len(routines), "automations": routines}


@router.post("/api/automations/{routine_id}/toggle")
async def toggle_automation(routine_id: str, req: ToggleAutomationRequest):
    """Enable or disable a background automation."""
    db = get_canonical_db()
    with db.get_connection() as conn:
        cur = conn.execute("UPDATE routines SET enabled = ? WHERE routine_id = ?", (int(req.enabled), routine_id))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Automation routine not found")
    return {"status": "success", "routine_id": routine_id, "enabled": req.enabled}


@router.post("/api/automations/{routine_id}/run")
async def run_automation_now(routine_id: str):
    """Trigger immediate execution of an automation routine."""
    engine = get_routine_engine()
    routines = {r.get("routine_id"): r for r in engine.list_routines()}
    if routine_id not in routines:
        raise HTTPException(status_code=404, detail="Automation routine not found")

    target = routines[routine_id]
    goal = target.get("goal") or target.get("name")

    from brjarvis.agent.task_state import get_task_state_manager
    from brjarvis.agent.executor import AgentExecutor
    import threading

    task_mgr = get_task_state_manager()
    task = task_mgr.create_task(goal=goal)

    def _run_bg():
        try:
            executor = AgentExecutor()
            executor.execute(goal, task_id=task.task_id)
        except Exception as e:
            logger.error("Automation run error: %s", e)

    threading.Thread(target=_run_bg, daemon=True).start()
    return {"status": "started", "routine_id": routine_id, "task_id": task.task_id}


@router.get("/api/automations/{routine_id}/history")
async def get_automation_history(routine_id: str, limit: int = 20):
    """Get past execution runs for an automation routine."""
    db = get_canonical_db()
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM routine_runs WHERE routine_id = ? ORDER BY executed_at DESC LIMIT ?",
            (routine_id, limit),
        ).fetchall()
        return {
            "routine_id": routine_id,
            "total": len(rows),
            "runs": [dict(r) for r in rows],
        }
