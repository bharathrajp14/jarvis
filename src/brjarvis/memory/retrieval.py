# memory/retrieval.py — Multi-Signal Hybrid Retrieval & Explainable Ranking Engine
"""
Hybrid Memory Retrieval and Ranking Pipeline for BR JARVIS.
Combines:
1. Exact entity/attribute lookup
2. Structured metadata filtering (scope, project, active validity)
3. Lexical matching (token overlap / BM25)
4. Semantic vector similarity (with automatic graceful fallback on vector failure)
Ranks using an explainable, multi-factor scoring model.
"""
from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .domain import CanonicalMemory, MemoryStatus, MemoryType
from .store import CanonicalMemoryStore, get_canonical_store
from .vector_store import VectorMemory

logger = logging.getLogger("JARVIS.HybridRetrieval")


@dataclass
class RankedMemoryCandidate:
    """Memory retrieval result with full scoring breakdown and explainability."""
    memory: CanonicalMemory
    similarity: float = 0.0          # Semantic vector similarity (0.0 to 1.0)
    lexical_score: float = 0.0       # Keyword match score (0.0 to 1.0)
    confidence: float = 1.0          # Stored confidence (0.0 to 1.0)
    reliability: float = 1.0         # Source reliability (0.0 to 1.0)
    temporal_score: float = 1.0      # Recency decay score (0.0 to 1.0)
    scope_score: float = 1.0         # Project/scope relevance multiplier
    final_score: float = 0.0         # Composite weighted ranking score
    selection_reason: str = ""       # Human-readable justification

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory.memory_id,
            "entity": self.memory.entity,
            "attribute": self.memory.attribute,
            "content": self.memory.content,
            "memory_type": self.memory.memory_type.value,
            "project_id": self.memory.project_id,
            "scope": self.memory.scope,
            "similarity": round(self.similarity, 4),
            "lexical_score": round(self.lexical_score, 4),
            "confidence": round(self.confidence, 4),
            "reliability": round(self.reliability, 4),
            "temporal_score": round(self.temporal_score, 4),
            "scope_score": round(self.scope_score, 4),
            "final_score": round(self.final_score, 4),
            "selection_reason": self.selection_reason,
        }


class HybridRetrievalEngine:
    """Production Multi-Signal Memory Search and Ranking Engine."""

    def __init__(
        self,
        store: Optional[CanonicalMemoryStore] = None,
        vector_store: Optional[VectorMemory] = None,
    ):
        self.store = store or get_canonical_store()
        self.vector = vector_store
        self._vector_attempted = False

    def _get_vector_store(self) -> Optional[VectorMemory]:
        if self.vector is None and not self._vector_attempted:
            self._vector_attempted = True
            try:
                self.vector = VectorMemory()
            except Exception as e:
                logger.warning("Vector memory store unavailable, using lexical/structured fallback: %s", e)
                self.vector = None
        return self.vector

    def search(
        self,
        query: str,
        project_id: str = "global",
        scope: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 5,
        min_score: float = 0.25,
    ) -> List[RankedMemoryCandidate]:
        """Execute hybrid search pipeline and return ranked candidates with explanations."""
        if not query or not query.strip():
            return []

        q_clean = query.strip()
        q_lower = q_clean.lower()
        now = time.time()

        candidate_map: Dict[str, CanonicalMemory] = {}

        # 1. Exact entity & attribute lookup
        exact_terms = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", q_clean)
        for term in exact_terms[:4]:
            with self.store.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM canonical_memories
                    WHERE (LOWER(entity) = ? OR LOWER(attribute) = ?)
                      AND status = 'ACTIVE'
                    """,
                    (term.lower(), term.lower()),
                )
                for row in cursor.fetchall():
                    mem = self.store._row_to_memory(row)
                    candidate_map[mem.memory_id] = mem

        # 2. Lexical / Keyword matching from canonical store
        lexical_hits = self.store.search_lexical(
            query=q_clean,
            project_id=project_id,
            scope=scope,
            limit=limit * 3,
        )
        for mem in lexical_hits:
            candidate_map[mem.memory_id] = mem

        # 3. Semantic Vector Search (with graceful fallback on failure)
        semantic_similarities: Dict[str, float] = {}
        vm = self._get_vector_store()
        if vm:
            try:
                v_results = vm.search(q_clean, top_k=limit * 2)
                for vr in v_results:
                    v_text = vr.get("text", "")
                    v_score = float(vr.get("score", 0.70))
                    # Link semantic match back to canonical memory if metadata matches
                    v_meta = vr.get("metadata", {})
                    mem_id = v_meta.get("memory_id")
                    if mem_id and mem_id in candidate_map:
                        semantic_similarities[mem_id] = v_score
                    else:
                        # Search by content snippet match
                        for cid, cm in candidate_map.items():
                            if cm.content and (cm.content in v_text or v_text in cm.content):
                                semantic_similarities[cid] = max(semantic_similarities.get(cid, 0.0), v_score)
            except Exception as v_err:
                logger.debug("Vector search fallback triggered: %s", v_err)

        # 4. If candidates are sparse, retrieve active memories by type/project
        if len(candidate_map) < limit:
            active_mems = self.store.list_active(project_id=project_id, scope=scope, limit=limit * 2)
            for mem in active_mems:
                if mem.memory_id not in candidate_map:
                    candidate_map[mem.memory_id] = mem

        # 5. Filter by memory_types if specified
        if memory_types:
            type_set = set(memory_types)
            candidate_map = {cid: m for cid, m in candidate_map.items() if m.memory_type in type_set}

        # 6. Multi-Factor Scoring & Ranking
        ranked_candidates: List[RankedMemoryCandidate] = []
        # Tokenize query for lexical scoring (support 2+ char tokens like OS, DB, UI, AI, CI)
        q_words = set(re.findall(r"\b\w{2,}\b", q_lower))

        for mem in candidate_map.values():
            if not mem.is_currently_effective(now):
                continue

            # a. Lexical score
            haystack = f"{mem.entity} {mem.attribute} {mem.content} {' '.join(mem.tags)}".lower()
            if q_lower in haystack:
                lexical_score = 1.00
            elif q_words:
                matched_words = sum(1 for w in q_words if (w in haystack or any(w in part for part in haystack.split())))
                lexical_score = min(1.0, matched_words / len(q_words))
            else:
                lexical_score = 0.10

            # b. Semantic score
            similarity = semantic_similarities.get(mem.memory_id, 0.50 if lexical_score > 0.4 else 0.0)

            # c. Temporal recency decay (45-day half-life)
            age_days = max(0.0, (now - mem.updated_at) / 86400.0)
            temporal_score = math.exp(-age_days / 45.0)

            # d. Scope boost
            scope_score = 1.25 if (project_id != "global" and mem.project_id == project_id) else 1.00
            if mem.scope == "project" and project_id != "global":
                scope_score *= 1.15

            # e. Composite score calculation
            # Weights: Semantic (0.35), Lexical (0.25), Reliability (0.15), Confidence (0.10), Temporal (0.15) * Scope
            importance_multiplier = 0.75 + (0.50 * mem.importance)
            base_score = (
                (0.35 * similarity)
                + (0.25 * lexical_score)
                + (0.15 * mem.reliability)
                + (0.10 * mem.confidence)
                + (0.15 * temporal_score)
            ) * scope_score * importance_multiplier

            # Penalties
            if mem.status == MemoryStatus.SUPERSEDED:
                base_score *= 0.10
            elif mem.status == MemoryStatus.CONFLICTED:
                base_score *= 0.50

            final_score = min(1.0, max(0.0, base_score))

            if final_score >= min_score:
                # Generate explainable selection justification
                reasons = []
                if lexical_score >= 0.3:
                    reasons.append("keyword match")
                if similarity >= 0.7:
                    reasons.append("strong semantic similarity")
                if mem.source_type.default_reliability >= 0.7:
                    reasons.append(f"verified source ({mem.source_type.value})")
                if mem.project_id == project_id and project_id != "global":
                    reasons.append(f"scoped to project '{project_id}'")
                if not reasons:
                    reasons.append("relevant active memory fact")

                reason_text = f"Selected because of {', '.join(reasons)} (score: {final_score:.2f})."

                ranked_candidates.append(
                    RankedMemoryCandidate(
                        memory=mem,
                        similarity=similarity,
                        lexical_score=lexical_score,
                        confidence=mem.confidence,
                        reliability=mem.reliability,
                        temporal_score=temporal_score,
                        scope_score=scope_score,
                        final_score=final_score,
                        selection_reason=reason_text,
                    )
                )

        # Sort descending by final score
        ranked_candidates.sort(key=lambda x: x.final_score, reverse=True)
        return ranked_candidates[:limit]


_GLOBAL_RETRIEVAL_ENGINE: Optional[HybridRetrievalEngine] = None


def get_retrieval_engine() -> HybridRetrievalEngine:
    """Return singleton HybridRetrievalEngine."""
    global _GLOBAL_RETRIEVAL_ENGINE
    if _GLOBAL_RETRIEVAL_ENGINE is None:
        _GLOBAL_RETRIEVAL_ENGINE = HybridRetrievalEngine()
    return _GLOBAL_RETRIEVAL_ENGINE
