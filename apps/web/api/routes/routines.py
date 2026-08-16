# api/routes/routines.py — Background Automation Routines Endpoints
from __future__ import annotations

import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from actions.routine_engine import get_routine_engine, TriggerType

router = APIRouter(tags=["Routines"])


class CreateRoutineRequest(BaseModel):
    name: str
    goal: str
    trigger_type: str = "schedule"
    trigger_config: Optional[Dict[str, Any]] = None
    skill_name: Optional[str] = None
    target_device: str = "pc"
    requires_approval: bool = False


@router.get("/api/agent/routines")
async def list_agent_routines():
    """List persistent background routines."""
    engine = get_routine_engine()
    routines = engine.list_routines()
    return {"total": len(routines), "routines": [r.to_dict() for r in routines]}


@router.post("/api/agent/routines")
async def create_agent_routine(req: CreateRoutineRequest):
    """Create a new background automation routine."""
    engine = get_routine_engine()
    try:
        trig = TriggerType(req.trigger_type)
    except ValueError:
        trig = TriggerType.SCHEDULE

    r = engine.create_routine(
        name=req.name,
        goal=req.goal,
        trigger_type=trig,
        trigger_config=req.trigger_config,
        skill_name=req.skill_name,
        target_device=req.target_device,
        requires_approval=req.requires_approval
    )
    return {"status": "created", "routine": r.to_dict()}


@router.post("/api/agent/routines/{routine_id}/run")
async def run_agent_routine(routine_id: str):
    """Trigger immediate execution of a background routine."""
    engine = get_routine_engine()
    res = await asyncio.to_thread(engine.run_routine_now, routine_id)
    return res
