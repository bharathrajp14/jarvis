# api/routes/skills.py — Declarative Skills & Workflows Endpoints
from __future__ import annotations

import time
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from brjarvis.skills.skill_engine import get_skill_engine

router = APIRouter(tags=["Skills"])

_SKILLS_CACHE: list[dict] | None = None
_SKILLS_CACHE_TS = 0.0
_CACHE_TTL_SECONDS = 5.0


class RunSkillRequest(BaseModel):
    inputs: Dict[str, Any] = {}


@router.get("/api/skills")
async def get_skills_list():
    """List user-invocable skills."""
    global _SKILLS_CACHE, _SKILLS_CACHE_TS
    now = time.time()
    if _SKILLS_CACHE is not None and (now - _SKILLS_CACHE_TS) < _CACHE_TTL_SECONDS:
        return _SKILLS_CACHE

    from brjarvis.skills import load_skills
    skills = [s for s in load_skills() if s.user_invocable]
    payload = [{"name": s.name, "description": s.description, "triggers": s.triggers} for s in skills]
    _SKILLS_CACHE = payload
    _SKILLS_CACHE_TS = now
    return payload


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
