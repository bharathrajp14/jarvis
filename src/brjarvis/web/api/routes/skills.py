# api/routes/skills.py — Declarative Skills & Workflows Endpoints
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from brjarvis.skills.skill_engine import get_skill_engine

logger = logging.getLogger("JARVIS.API.Skills")
router = APIRouter(tags=["Skills"])

_SKILLS_CACHE: list[dict] | None = None
_SKILLS_CACHE_TS = 0.0
_CACHE_TTL_SECONDS = 5.0


class RunSkillRequest(BaseModel):
    inputs: Dict[str, Any] = {}


@router.get("/api/skills")
async def get_skills_list():
    """List all user-invocable and declarative skills."""
    global _SKILLS_CACHE, _SKILLS_CACHE_TS
    now = time.time()
    if _SKILLS_CACHE is not None and (now - _SKILLS_CACHE_TS) < _CACHE_TTL_SECONDS:
        return _SKILLS_CACHE

    payload = []
    try:
        try:
            from brjarvis.skills import load_skills
        except ImportError:
            from skills import load_skills

        for s in load_skills():
            triggers = getattr(s, "triggers", []) or [f"/{s.name}"]
            payload.append({
                "name": s.name,
                "description": s.description or "Built-in automation skill.",
                "triggers": triggers,
                "command": triggers[0] if triggers else f"/{s.name}",
                "user_invocable": getattr(s, "user_invocable", True),
                "argument_hint": getattr(s, "argument_hint", ""),
                "type": "template",
            })
    except Exception as e:
        logger.warning(f"Error loading prompt skills: {e}")

    try:
        engine = get_skill_engine()
        for ds in engine.list_skills():
            if not any(p["name"] == ds.name for p in payload):
                payload.append({
                    "name": ds.name,
                    "description": ds.description or "Declarative workflow capability.",
                    "triggers": [f"/{ds.name}"],
                    "command": f"/{ds.name}",
                    "user_invocable": True,
                    "argument_hint": "inputs JSON",
                    "type": "declarative",
                })
    except Exception as e:
        logger.warning(f"Error loading declarative skills: {e}")

    res_data = {"total": len(payload), "skills": payload}
    _SKILLS_CACHE = res_data
    _SKILLS_CACHE_TS = now
    return res_data


@router.get("/api/agent/skills/declarative")
async def list_declarative_skills():
    """List all declarative versioned skills."""
    engine = get_skill_engine()
    skills = engine.list_skills()
    return {"total": len(skills), "skills": [s.to_dict() for s in skills]}


@router.post("/api/agent/skills/{name}/run")
async def run_declarative_skill(name: str, req: RunSkillRequest):
    """Execute a declarative skill by name with supplied input values."""
    engine = get_skill_engine()
    res = await asyncio.to_thread(engine.execute_skill, name, req.inputs)
    return res
