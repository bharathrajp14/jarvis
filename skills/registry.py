# skills/registry.py
"""
Skill Registry: High-level search, category grouping, and discovery interface
for BR JARVIS's 400+ domain skills.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional
from skills.loader import SkillDef, load_skills, find_skill

_cached_skills_list: List[SkillDef] = []
_last_skills_load_time: float = 0.0
_SKILL_CACHE_TTL: float = 30.0  # seconds


def _get_cached_skills(force_reload: bool = False) -> List[SkillDef]:
    global _cached_skills_list, _last_skills_load_time
    now = time.time()
    if force_reload or not _cached_skills_list or (now - _last_skills_load_time) > _SKILL_CACHE_TTL:
        _cached_skills_list = load_skills()
        _last_skills_load_time = now
    return _cached_skills_list


def get_all_skills() -> List[SkillDef]:
    """Return all registered skills."""
    return _get_cached_skills()


def get_skills_by_category() -> Dict[str, List[SkillDef]]:
    """Group all skills by category."""
    grouped: Dict[str, List[SkillDef]] = {}
    for skill in _get_cached_skills():
        cat = skill.category or "general"
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(skill)
    return grouped


def search_skills(query: str, max_results: int = 15) -> List[SkillDef]:
    """Search skills by name, description, category, domain, or triggers."""
    skills = _get_cached_skills()
    q = query.lower().strip()
    if not q:
        return skills[:max_results]

    results: List[tuple[int, SkillDef]] = []
    for skill in skills:
        score = 0
        name = skill.name.lower()
        desc = skill.description.lower()
        cat = skill.category.lower()
        domain = skill.domain.lower()

        if q == name or q == f"/{name}":
            score += 100
        elif q in name:
            score += 50
        if any(q in t.lower() for t in skill.triggers):
            score += 40
        if q in cat or q in domain:
            score += 30
        if q in desc:
            score += 20

        if score > 0:
            results.append((score, skill))

    results.sort(key=lambda x: x[0], reverse=True)
    return [skill for _, skill in results[:max_results]]


def list_skill_categories() -> Dict[str, int]:
    """Return category names mapped to skill counts."""
    categories: Dict[str, int] = {}
    for skill in _get_cached_skills():
        cat = skill.category or "general"
        categories[cat] = categories.get(cat, 0) + 1
    return dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))
