# evolution/__init__.py — BR JARVIS v41.0 Self-Improvement Subsystem
"""
The evolution subsystem provides the cognitive feedback loop for BR JARVIS.

It analyses operational experience (LessonStore + ExperienceReplay) to
synthesise actionable ImprovementProposals without modifying source code.

Primary entry point::

    from brjarvis.evolution import get_evolution_engine, SelfImprovementEngine

Example usage::

    engine = get_evolution_engine()
    proposals = engine.analyse()
    for p in proposals:
        print(f"[{p.source}] {p.topic}: {p.action}")
"""

from __future__ import annotations

from brjarvis.evolution.engine import (
    ImprovementProposal,
    SelfImprovementEngine,
    get_evolution_engine,
)

__all__ = [
    "ImprovementProposal",
    "SelfImprovementEngine",
    "get_evolution_engine",
]
