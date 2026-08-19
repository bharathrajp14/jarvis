# evolution/engine.py — Self-Improvement Engine — BR JARVIS v41.0 (MARK XLI)
"""
SelfImprovementEngine: The cognitive feedback loop for BR JARVIS.

Reads operational experience and user corrections from the memory subsystem,
identifies recurring patterns (both successes and failures), synthesises
actionable learning cycles, and writes structured improvement proposals to
the guardian audit log.

Architecture:
- Reads from   memory.lessons.LessonStore
- Reads from   memory.experience_replay (successes/failures)
- Writes to    guardian.audit_log
- Exposes      analyse(), get_top_lessons(), propose_improvements()

This module is intentionally stateless between calls — all state lives in
the SQLite-backed memory subsystem, making it crash-safe and restartable.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.Evolution")


@dataclass
class ImprovementProposal:
    """
    A structured, actionable improvement proposal produced by the evolution engine.

    Attributes:
        topic:          The subject area or skill domain the improvement relates to.
        lesson:         The learned rule or correction derived from experience.
        source:         Origin of the signal (``"lesson"``, ``"failure"``, ``"success"``).
        confidence:     0.0–1.0 confidence the proposal is valid and non-redundant.
        action:         Human-readable recommended action for the system or user.
        created_at:     Unix timestamp of proposal creation.
    """

    topic: str
    lesson: str
    source: str
    confidence: float
    action: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "lesson": self.lesson,
            "source": self.source,
            "confidence": self.confidence,
            "action": self.action,
            "created_at": self.created_at,
        }


class SelfImprovementEngine:
    """
    Cognitive feedback loop for BR JARVIS v41.0.

    Periodically analyses operational memory to extract high-value lessons
    and surface actionable improvement proposals.  Does not modify source
    code or tool schemas — it surfaces proposals to the guardian audit log
    for human review and downstream system tuning.

    Usage::

        engine = SelfImprovementEngine()
        proposals = engine.analyse()
        for p in proposals:
            print(p.topic, "→", p.action)
    """

    #: Minimum lesson weight to be considered for an improvement proposal.
    MIN_LESSON_WEIGHT: float = 0.5
    #: Maximum number of lessons to analyse per cycle.
    MAX_LESSONS_PER_CYCLE: int = 50
    #: Maximum number of experience records per cycle.
    MAX_EXPERIENCE_PER_CYCLE: int = 30

    def __init__(self) -> None:
        self._lesson_store = self._load_lesson_store()
        logger.info("🧬 SelfImprovementEngine initialised")

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _load_lesson_store():
        """Lazily import and return the LessonStore singleton."""
        try:
            from brjarvis.memory.lessons import LessonStore
            return LessonStore()
        except Exception as exc:
            logger.warning("LessonStore unavailable: %s", exc)
            return None

    @staticmethod
    def _load_experience_store():
        """Lazily import and return the ExperienceReplay store."""
        try:
            from brjarvis.memory.experience_replay import ExperienceReplay
            return ExperienceReplay()
        except Exception as exc:
            logger.debug("ExperienceReplay unavailable: %s", exc)
            return None

    # ── Public API ────────────────────────────────────────────────────────────

    def get_top_lessons(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Return the *limit* highest-weighted lessons from the LessonStore.

        Each lesson dict contains at minimum:
        ``topic``, ``correction``, ``source``, ``weight``.
        """
        if not self._lesson_store:
            return []
        try:
            lessons = self._lesson_store.list_lessons(limit=self.MAX_LESSONS_PER_CYCLE)
            # Sort by weight descending and return top *limit*
            weighted = sorted(lessons, key=lambda les: les.get("weight", 1.0), reverse=True)
            return weighted[:limit]
        except Exception as exc:
            logger.warning("get_top_lessons error: %s", exc)
            return []

    def analyse(self) -> List[ImprovementProposal]:
        """
        Run a full improvement analysis cycle.

        Returns a list of :class:`ImprovementProposal` objects, ordered by
        descending confidence.  An empty list is returned when insufficient
        data is available.
        """
        proposals: List[ImprovementProposal] = []

        # ── 1. Mine high-weight user corrections / lessons ────────────────────
        lessons = self.get_top_lessons(limit=self.MAX_LESSONS_PER_CYCLE)
        for lesson in lessons:
            weight = lesson.get("weight", 1.0)
            if weight < self.MIN_LESSON_WEIGHT:
                continue
            topic = lesson.get("topic", "general")
            correction = lesson.get("correction", "")
            source = lesson.get("source", "lesson")
            if not correction:
                continue

            # Confidence scales with lesson weight (clamped to [0.3, 0.99])
            confidence = min(0.99, max(0.3, weight / 5.0))
            proposals.append(
                ImprovementProposal(
                    topic=topic,
                    lesson=correction,
                    source=source,
                    confidence=confidence,
                    action=f"Reinforce pattern: {correction[:120]}",
                )
            )

        # ── 2. Mine experience replay for repeated failures ───────────────────
        experience_store = self._load_experience_store()
        if experience_store:
            try:
                failures = experience_store.get_failures(
                    limit=self.MAX_EXPERIENCE_PER_CYCLE
                )
                for failure in failures:
                    goal = failure.get("goal_query", "unknown goal")
                    reason = failure.get("failure_reason", "")
                    if not reason:
                        continue
                    proposals.append(
                        ImprovementProposal(
                            topic="failure_pattern",
                            lesson=f"Goal '{goal[:60]}' failed: {reason[:120]}",
                            source="failure",
                            confidence=0.75,
                            action=f"Avoid approach that caused: {reason[:80]}",
                        )
                    )
            except Exception as exc:
                logger.debug("Experience failure mining error: %s", exc)

        # Sort by confidence descending
        proposals.sort(key=lambda p: p.confidence, reverse=True)

        logger.info(
            "🧬 Evolution cycle complete: %d proposals generated", len(proposals)
        )
        self._log_cycle(proposals)
        return proposals

    def propose_improvements(self, context: str = "") -> List[ImprovementProposal]:
        """
        Alias for :meth:`analyse` — returns contextually filtered proposals.

        When *context* is provided, proposals whose ``lesson`` or ``topic``
        overlaps with the context string are ranked higher.
        """
        proposals = self.analyse()
        if not context:
            return proposals

        context_lower = context.lower()

        def relevance(p: ImprovementProposal) -> float:
            score = p.confidence
            if context_lower in p.topic.lower() or context_lower in p.lesson.lower():
                score += 0.15
            return score

        return sorted(proposals, key=relevance, reverse=True)

    # ── Audit logging ─────────────────────────────────────────────────────────

    def _log_cycle(self, proposals: List[ImprovementProposal]) -> None:
        """Write improvement cycle results to the guardian audit log."""
        if not proposals:
            return
        try:
            from brjarvis.guardian.audit_log import get_audit_log
            audit = get_audit_log()
            audit.log_event(
                event_type="evolution.cycle",
                detail={
                    "proposal_count": len(proposals),
                    "top_proposal": proposals[0].to_dict() if proposals else None,
                },
            )
        except Exception as exc:
            logger.debug("Guardian audit log unavailable: %s", exc)


# ── Module-Level Singleton ────────────────────────────────────────────────────

_engine: Optional[SelfImprovementEngine] = None


def get_evolution_engine() -> SelfImprovementEngine:
    """Return the process-wide singleton SelfImprovementEngine."""
    global _engine
    if _engine is None:
        _engine = SelfImprovementEngine()
    return _engine


__all__ = [
    "ImprovementProposal",
    "SelfImprovementEngine",
    "get_evolution_engine",
]
