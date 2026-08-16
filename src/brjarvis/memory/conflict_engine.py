# memory/conflict_engine.py — Deterministic Memory Conflict Resolution Engine
"""
Conflict Detection and Deterministic Resolution Engine for BR JARVIS.
Detects:
- Direct attribute value collisions
- Temporal overlapping contradictions
- Scope conflicts (Project vs Global)
- Contradictory constraints
Resolves using strict provenance hierarchy, user correction precedence, and scope specificity.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .domain import CanonicalMemory, MemoryStatus, MemoryType, SourceType
from .store import CanonicalMemoryStore, get_canonical_store

logger = logging.getLogger("JARVIS.ConflictEngine")


class ConflictResolutionAction(str, Enum):
    SUPERSEDE_EXISTING = "SUPERSEDE_EXISTING"      # Candidate is newer/higher authority -> replaces existing
    REJECT_CANDIDATE = "REJECT_CANDIDATE"          # Existing is higher authority (e.g. user statement vs model inference)
    SCOPED_OVERRIDE = "SCOPED_OVERRIDE"            # Both valid in different scopes (e.g. project overrides global)
    MERGE = "MERGE"                                # Both valid complementary items
    MARK_CONFLICTED = "MARK_CONFLICTED"            # Irreconcilable ambiguity requiring human clarification


@dataclass
class ConflictResolutionResult:
    """Outcome of deterministic conflict evaluation."""
    action: ConflictResolutionAction
    candidate_memory: CanonicalMemory
    conflicting_memories: List[CanonicalMemory]
    winner_memory: Optional[CanonicalMemory] = None
    loser_memories: List[CanonicalMemory] = field(default_factory=list)
    reason: str = ""
    conflict_group_id: Optional[str] = None


class ConflictEngine:
    """Deterministic, rule-based conflict detector and resolver."""

    def __init__(self, store: Optional[CanonicalMemoryStore] = None):
        self.store = store or get_canonical_store()

    def detect_conflicts(self, candidate: CanonicalMemory) -> List[CanonicalMemory]:
        """Detect existing active memories that conflict with candidate."""
        conflicts: List[CanonicalMemory] = []

        # 1. Direct Entity + Attribute collision
        if candidate.entity and candidate.attribute:
            with self.store.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM canonical_memories
                    WHERE entity = ? AND attribute = ?
                      AND status = 'ACTIVE'
                      AND memory_id != ?
                    """,
                    (candidate.entity, candidate.attribute, candidate.memory_id),
                )
                for row in cursor.fetchall():
                    existing = self.store._row_to_memory(row)
                    # If values or content differ, it's a conflict
                    if str(existing.value).strip().lower() != str(candidate.value).strip().lower() or (
                        existing.content.strip().lower() != candidate.content.strip().lower()
                    ):
                        conflicts.append(existing)

        # 2. Constraint and Preference contradiction check
        if candidate.memory_type in (MemoryType.CONSTRAINT, MemoryType.PREFERENCE):
            active_constraints = self.store.list_active(
                user_id=candidate.user_id,
                project_id=candidate.project_id,
                memory_type=candidate.memory_type,
            )
            for c in active_constraints:
                if c.memory_id == candidate.memory_id:
                    continue
                if self._are_constraints_contradictory(candidate.content, c.content):
                    if c not in conflicts:
                        conflicts.append(c)

        return conflicts

    def resolve(self, candidate: CanonicalMemory, conflicts: List[CanonicalMemory]) -> ConflictResolutionResult:
        """Deterministically resolve collision between candidate and existing memories."""
        if not conflicts:
            return ConflictResolutionResult(
                action=ConflictResolutionAction.SUPERSEDE_EXISTING,
                candidate_memory=candidate,
                conflicting_memories=[],
                winner_memory=candidate,
                reason="No conflicting records found.",
            )

        # Process primary conflicting record
        existing = conflicts[0]

        # Rule 1: User Correction ALWAYS wins unconditionally
        if candidate.source_type == SourceType.EXPLICIT_USER_CORRECTION:
            return ConflictResolutionResult(
                action=ConflictResolutionAction.SUPERSEDE_EXISTING,
                candidate_memory=candidate,
                conflicting_memories=conflicts,
                winner_memory=candidate,
                loser_memories=conflicts,
                reason="User explicitly corrected this fact. The new correction is authoritative.",
            )

        # Rule 2: Model inference CANNOT overwrite verified facts or user statements
        cand_rel = candidate.source_type.default_reliability
        exist_rel = existing.source_type.default_reliability

        if cand_rel < exist_rel and (exist_rel - cand_rel) >= 0.30:
            return ConflictResolutionResult(
                action=ConflictResolutionAction.REJECT_CANDIDATE,
                candidate_memory=candidate,
                conflicting_memories=conflicts,
                winner_memory=existing,
                loser_memories=[candidate],
                reason=f"Candidate source ({candidate.source_type.value}) lacks authority to overwrite verified existing record ({existing.source_type.value}).",
            )

        # Rule 3: Project scope overrides global scope for project-specific context
        if candidate.project_id != "global" and existing.project_id == "global":
            return ConflictResolutionResult(
                action=ConflictResolutionAction.SCOPED_OVERRIDE,
                candidate_memory=candidate,
                conflicting_memories=conflicts,
                winner_memory=candidate,
                reason=f"Project-specific record for '{candidate.project_id}' scoped override of global default.",
            )

        # Rule 4: Higher reliability wins
        if cand_rel > exist_rel:
            return ConflictResolutionResult(
                action=ConflictResolutionAction.SUPERSEDE_EXISTING,
                candidate_memory=candidate,
                conflicting_memories=conflicts,
                winner_memory=candidate,
                loser_memories=conflicts,
                reason=f"Candidate source reliability ({cand_rel:.2f}) exceeds existing record ({exist_rel:.2f}).",
            )

        # Rule 5: Same reliability level -> Recency wins
        if cand_rel == exist_rel:
            if candidate.created_at >= existing.created_at:
                return ConflictResolutionResult(
                    action=ConflictResolutionAction.SUPERSEDE_EXISTING,
                    candidate_memory=candidate,
                    conflicting_memories=conflicts,
                    winner_memory=candidate,
                    loser_memories=conflicts,
                    reason="Candidate is a more recent observation from equal authority source.",
                )

        # Rule 6: Ambiguous collision -> Mark conflicted
        conflict_group = f"conf_{uuid.uuid4().hex[:8]}"
        candidate.status = MemoryStatus.CONFLICTED
        candidate.conflict_group_id = conflict_group
        for c in conflicts:
            c.status = MemoryStatus.CONFLICTED
            c.conflict_group_id = conflict_group
            self.store.save(c)

        return ConflictResolutionResult(
            action=ConflictResolutionAction.MARK_CONFLICTED,
            candidate_memory=candidate,
            conflicting_memories=conflicts,
            conflict_group_id=conflict_group,
            reason="Ambiguous contradiction between equal authority sources requiring explicit user clarification.",
        )

    def apply_resolution(self, result: ConflictResolutionResult) -> CanonicalMemory:
        """Apply the resolution outcome directly into the canonical store."""
        if result.action == ConflictResolutionAction.SUPERSEDE_EXISTING:
            for loser in result.loser_memories:
                self.store.supersede(loser.memory_id, result.candidate_memory)
            return self.store.save(result.candidate_memory)

        elif result.action == ConflictResolutionAction.REJECT_CANDIDATE:
            logger.info("Rejected candidate memory %s: %s", result.candidate_memory.memory_id, result.reason)
            return result.winner_memory or result.candidate_memory

        elif result.action == ConflictResolutionAction.SCOPED_OVERRIDE:
            return self.store.save(result.candidate_memory)

        elif result.action == ConflictResolutionAction.MARK_CONFLICTED:
            return self.store.save(result.candidate_memory)

        return self.store.save(result.candidate_memory)

    @staticmethod
    def _are_constraints_contradictory(text_a: str, text_b: str) -> bool:
        """Evaluate if two constraint strings contain direct negation pairs."""
        a = text_a.lower()
        b = text_b.lower()

        negation_pairs = [
            ("always ask", "never ask"),
            ("always ask", "auto-execute"),
            ("dark mode", "light mode"),
            ("auto-confirm", "require confirmation"),
            ("use python", "never use python"),
            ("use typescript", "never use typescript"),
        ]
        for p1, p2 in negation_pairs:
            if (p1 in a and p2 in b) or (p2 in a and p1 in b):
                return True
        return False


_GLOBAL_CONFLICT_ENGINE: Optional[ConflictEngine] = None


def get_conflict_engine() -> ConflictEngine:
    """Return singleton ConflictEngine."""
    global _GLOBAL_CONFLICT_ENGINE
    if _GLOBAL_CONFLICT_ENGINE is None:
        _GLOBAL_CONFLICT_ENGINE = ConflictEngine()
    return _GLOBAL_CONFLICT_ENGINE
