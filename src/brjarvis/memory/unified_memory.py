# memory/unified_memory.py — Master Multi-Tier Memory Coordinator
"""
Master Unified Memory Coordinator for BR JARVIS.
Integrates:
- Canonical SQLite WAL Store (authoritative ground truth)
- Temporal State & Timeline Tracking
- Deterministic Conflict Resolution Engine
- Hybrid Multi-Signal Retrieval & Ranking
- Derived Vector Embeddings (ChromaDB + TF-IDF fallback)
- Non-destructive Session Lifecycle
- Operational Lessons & Experience Replay
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Union

from brjarvis.core.runtime import get_runtime

from .archiver import MemoryArchiver
from .cache import MemoryCache
from .conflict_engine import get_conflict_engine
from .domain import (
    CanonicalMemory,
    MemoryStatus,
    MemoryType,
    SourceType,
)
from .experience_replay import ExperienceTrajectory, get_experience_replay
from .lessons import LessonStore
from .reflection import ReflectionEngine
from .retrieval import RankedMemoryCandidate, get_retrieval_engine
from .store import get_canonical_store
from .temporal import get_temporal_engine
from .vector_store import VectorMemory
from .working import WorkingMemory

logger = logging.getLogger("JARVIS.UnifiedMemory")


class UnifiedMemoryManager:
    """Single master memory coordinator for BR JARVIS."""

    def __init__(self):
        self.store = get_canonical_store()
        self.temporal = get_temporal_engine()
        self.conflicts = get_conflict_engine()
        self.vector = VectorMemory()
        self.retrieval = get_retrieval_engine()

        self.working = WorkingMemory(max_tokens=100_000)
        self.cache = MemoryCache(default_ttl=300.0)
        self.archiver = MemoryArchiver(max_age_days=30)
        self.lessons = LessonStore()
        self.experience = get_experience_replay()
        self.reflection = ReflectionEngine(self.lessons)

        # Hook store invalidation into caches and vector index
        self.store.register_invalidation_hook(self._on_store_invalidated)

        # Register self in DI Container
        try:
            runtime = get_runtime()
            runtime.container.register_instance(UnifiedMemoryManager, self)
        except Exception:
            pass

        logger.info("⚡ UnifiedMemoryManager initialized with Canonical WAL Store + Temporal Conflict Engine")

    def _on_store_invalidated(self, memory_id: str, content: Optional[str]) -> None:
        self.cache.clear()
        VectorMemory._RECALL_CACHE.clear()

    # ── Working Memory ────────────────────────────────────────────────────────

    def add_interaction(self, role: str, content: str) -> None:
        """Add turn to active working memory."""
        self.working.add(role, content)

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Retrieve active conversation history."""
        return self.working.get()

    def add_user_message(self, content: str) -> None:
        self.add_interaction("user", content)

    def add_assistant_message(self, content: str) -> None:
        self.add_interaction("assistant", content)

    # ── Canonical Memory Operations ───────────────────────────────────────────

    def remember(
        self,
        name_or_memory: Union[str, CanonicalMemory],
        content: str = "",
        description: str = "",
        mem_type: str = "user",
        scope: str = "user",
        confidence: float = 1.0,
        source: str = "user",
        project_id: str = "global",
        entity: str = "",
        attribute: str = "",
        value: Any = "",
    ) -> CanonicalMemory:
        """
        Store a new memory through the conflict detection and resolution engine.
        Guarantees deterministic state evolution, provenance, and derived index sync.
        Supports passing a CanonicalMemory object directly or individual attributes.
        """
        if isinstance(name_or_memory, CanonicalMemory):
            candidate = name_or_memory
        else:
            name = str(name_or_memory)
            ent = entity or name
            attr = attribute or name
            val = value or content

            candidate = CanonicalMemory(
                entity=ent,
                attribute=attr,
                value=val,
                content=content,
                memory_type=MemoryType.from_str(mem_type),
                scope=scope,
                project_id=project_id,
                confidence=confidence,
                source_type=SourceType.from_str(source),
                status=MemoryStatus.ACTIVE,
            )

        # Detect and resolve conflicts deterministically
        detected_conflicts = self.conflicts.detect_conflicts(candidate)
        resolution = self.conflicts.resolve(candidate, detected_conflicts)
        saved = self.conflicts.apply_resolution(resolution)

        # Sync to Vector Memory
        try:
            self.vector.store(
                text=f"{saved.entity} {saved.attribute}: {saved.content}",
                metadata={"memory_id": saved.memory_id, "type": saved.memory_type.value, "scope": saved.scope},
                doc_id=saved.memory_id,
            )
        except Exception as ve:
            logger.debug("Vector sync notice: %s", ve)

        logger.info(f"💾 Unified Memory saved: [{saved.scope}] {saved.entity} ({saved.status.value})")
        return saved

    def correct(
        self,
        entity: str,
        attribute: str,
        new_value: str,
        reason: str = "User explicit correction",
        project_id: str = "global",
        scope: str = "user",
    ) -> CanonicalMemory:
        """
        First-class User Correction pipeline.
        Creates authoritative correction with SourceType.EXPLICIT_USER_CORRECTION,
        immediately superseding previous stale state.
        """
        correction = CanonicalMemory(
            entity=entity,
            attribute=attribute,
            value=new_value,
            content=f"{entity} ({attribute}) = {new_value}",
            memory_type=MemoryType.USER_PROFILE if scope == "user" else MemoryType.PROJECT_STATE,
            scope=scope,
            project_id=project_id,
            confidence=1.0,
            reliability=1.0,
            source_type=SourceType.EXPLICIT_USER_CORRECTION,
            evidence=reason,
            status=MemoryStatus.ACTIVE,
        )

        existing_conflicts = self.conflicts.detect_conflicts(correction)
        resolution = self.conflicts.resolve(correction, existing_conflicts)
        saved = self.conflicts.apply_resolution(resolution)

        # Invalidate vector memory and replace with authoritative correction
        try:
            self.vector.store(
                text=f"{saved.entity} {saved.attribute}: {saved.content}",
                metadata={"memory_id": saved.memory_id, "type": saved.memory_type.value},
                doc_id=saved.memory_id,
            )
        except Exception as ve:
            logger.debug("Correction vector sync: %s", ve)

        logger.info(
            f"✨ User correction applied: {entity}/{attribute} -> {new_value} (Superseded {len(resolution.loser_memories)} older records)"
        )
        return saved

    def forget(self, name_or_id: str = "", entity: str = "", scope: Optional[str] = None) -> bool:
        """Soft-delete memory record and remove from all vector and cache indexes.

        FIXED (Phase 7): No longer uses direct SQL. Uses store.search_lexical()
        so invalidation hooks fire correctly and no raw DB access bypasses the store layer.

        Args:
            name_or_id: memory_id (mem_xxx) or entity name to look up
            entity:     alternative entity name lookup (used by memory_tools)
            scope:      optional scope filter (user/project/session)
        """
        lookup = entity or name_or_id
        target_id = ""

        if lookup.startswith("mem_"):
            target_id = lookup
        else:
            # Use the store's lexical search instead of direct SQL
            proj = "global"
            hits = self.store.search_lexical(
                query=lookup,
                project_id=proj,
                scope=scope,
                limit=5,
            )
            # Find exact entity match first
            for hit in hits:
                if hit.entity and hit.entity.lower() == lookup.lower():
                    target_id = hit.memory_id
                    break
            # Fall back to first result
            if not target_id and hits:
                target_id = hits[0].memory_id

        if not target_id:
            logger.warning("[UnifiedMemory] forget(): could not locate memory '%s'", lookup)
            return False

        success = self.store.delete(target_id, hard=False)
        self.cache.clear()
        # Use instance cache clear (class-level cache removed in Phase 2)
        if self.vector:
            self.vector._invalidate_cache()
        logger.info("[UnifiedMemory] Soft-deleted: %s (%s)", lookup, target_id)
        return success

    def search(
        self,
        query: str,
        limit: int = 5,
        project_id: str = "global",
    ) -> List[Dict[str, Any]]:
        """Convenience alias for hybrid recall search."""
        return self.recall(query=query, limit=limit, project_id=project_id)

    def recall(
        self,
        query: str,
        limit: int = 5,
        project_id: str = "global",
    ) -> List[Dict[str, Any]]:
        """Multi-signal hybrid recall with temporal and confidence ranking."""
        results: List[Dict[str, Any]] = []

        # 1. Search Canonical Memories via Hybrid Engine
        ranked_hits: List[RankedMemoryCandidate] = self.retrieval.search(
            query=query,
            project_id=project_id,
            limit=limit,
        )
        for h in ranked_hits:
            results.append(
                {
                    "source": "canonical_memory",
                    "memory_id": h.memory.memory_id,
                    "entity": h.memory.entity,
                    "attribute": h.memory.attribute,
                    "name": h.memory.entity or h.memory.attribute or "Memory",
                    "content": h.memory.content,
                    "scope": h.memory.scope,
                    "project_id": h.memory.project_id,
                    "confidence": h.confidence,
                    "reliability": h.reliability,
                    "type": h.memory.memory_type.value,
                    "retention_class": h.memory.retention_class.value
                    if hasattr(h.memory, "retention_class")
                    else "NORMAL",
                    "final_score": h.final_score,
                    "selection_reason": h.selection_reason,
                }
            )

        # 2. Search Operational Lessons
        try:
            lesson_hits = self.lessons.get_relevant_lessons(query, limit=2)
            for l in lesson_hits:
                results.append(
                    {
                        "source": "lesson",
                        "name": f"Lesson: {l.get('topic', '')}",
                        "content": l.get("correction", ""),
                        "confidence": float(l.get("confidence", 0.85)),
                        "final_score": 0.80,
                        "selection_reason": "Learned lesson from previous operational failure/correction.",
                    }
                )
        except Exception:
            pass

        # Sort descending by final score
        results.sort(key=lambda r: r.get("final_score", 0.5), reverse=True)
        return results[:limit]

    # ── Operational Learning & Experience Replay ──────────────────────────────

    def record_execution_experience(
        self,
        goal: str,
        success: bool,
        tool_sequence: List[str],
        failure_reason: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record trajectory into ExperienceReplayStore for pattern learning."""
        traj = ExperienceTrajectory(
            goal_query=goal,
            success_status=success,
            step_count=len(tool_sequence),
            tool_sequence=tool_sequence,
            failure_reason=failure_reason,
            execution_context=context or {},
        )
        self.experience.record_trajectory(traj)

    def get_relevant_experiences(self, goal: str, limit: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve similar successful patterns and known pitfalls for planner."""
        return {
            "successes": self.experience.get_successful_patterns(goal, limit=limit),
            "failures": self.experience.get_similar_failures(goal, limit=limit),
        }

    # ── Temporal Diagnostics ──────────────────────────────────────────────────

    def get_timeline(self, entity: str, attribute: str) -> List[Dict[str, Any]]:
        """Retrieve chronological evolution of fact."""
        return self.temporal.get_timeline(entity, attribute)

    def explain_fact(self, entity: str, attribute: str) -> str:
        """Generate human/agent explanation of fact history."""
        return self.temporal.explain_temporal_change(entity, attribute)

    def save(
        self, category: str = "operational", name: str = "", content: str = "", importance: float = 1.0, **kwargs
    ) -> CanonicalMemory:
        """Convenience alias for remember()."""
        return self.remember(
            name=name or f"mem_{int(time.time() * 1000)}",
            content=content,
            mem_type=category,
            confidence=importance,
            **kwargs,
        )

    def store(self, content: str, name: str = "", **kwargs) -> CanonicalMemory:
        """Convenience alias for remember()."""
        return self.remember(
            name=name or f"mem_{int(time.time() * 1000)}",
            content=content,
            **kwargs,
        )


_global_unified_memory: Optional[UnifiedMemoryManager] = None


def get_unified_memory() -> UnifiedMemoryManager:
    global _global_unified_memory
    if _global_unified_memory is None:
        _global_unified_memory = UnifiedMemoryManager()
    return _global_unified_memory
