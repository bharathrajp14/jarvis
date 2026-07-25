# memory/temporal_kg.py — Temporal Knowledge Graph 2.0 & World Model for BR JARVIS MK38
"""
Extends relational world modeling by storing time-stamped edges (e1, r, e2, t_start, t_end)
for temporal queries, state evolution playback, and point-in-time snapshot filtering.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from memory.persistent_store import get_memory_dir

logger = logging.getLogger("JARVIS.TemporalKG")


class TemporalEdge(BaseModel):
    """Time-stamped directed relational edge."""

    source_id: str
    target_id: str
    relationship: str
    valid_from: float = Field(default_factory=time.time, description="Epoch timestamp when edge became valid")
    valid_to: Optional[float] = Field(default=None, description="Epoch timestamp when edge was invalidated (None if currently valid)")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class TemporalKnowledgeGraph:
    """
    Temporal Relational World Model graph managing state mutations over time.
    """

    def __init__(self, db_dir: Optional[Path] = None):
        if db_dir is None:
            db_dir = get_memory_dir("user")
        db_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path = db_dir / "temporal_knowledge_graph.json"
        self._edges: List[TemporalEdge] = []
        self._load_ledger()

    def _load_ledger(self) -> None:
        """Load temporal edges from disk ledger."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self._edges = [TemporalEdge(**item) for item in data.get("edges", [])]
                logger.info(f"💾 TemporalKG loaded {len(self._edges)} temporal edges")
            except Exception as e:
                logger.warning(f"⚠️ TemporalKG load warning: {e}")
                self._edges = []

    def save_ledger(self) -> None:
        """Save temporal edges to disk ledger."""
        try:
            payload = {"edges": [edge.model_dump() for edge in self._edges]}
            self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"❌ TemporalKG save error: {e}")

    def add_temporal_relation(
        self,
        source_id: str,
        relationship: str,
        target_id: str,
        valid_from: Optional[float] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> TemporalEdge:
        """
        Add a new time-stamped relational edge. Invalidates previous active edge of same relation if present.
        """
        now = valid_from or time.time()

        # Invalidate current active edge of identical source + relationship if present
        for edge in self._edges:
            if edge.source_id == source_id and edge.relationship == relationship and edge.valid_to is None:
                edge.valid_to = now

        new_edge = TemporalEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            valid_from=now,
            attributes=attributes or {},
        )
        self._edges.append(new_edge)
        self.save_ledger()
        logger.debug(f"Added Temporal Edge: ({source_id}) -[{relationship}]-> ({target_id})")
        return new_edge

    def invalidate_relation(self, source_id: str, relationship: str, target_id: str, invalid_at: Optional[float] = None) -> bool:
        """Invalidate an active temporal relation."""
        now = invalid_at or time.time()
        invalidated = False
        for edge in self._edges:
            if edge.source_id == source_id and edge.target_id == target_id and edge.relationship == relationship and edge.valid_to is None:
                edge.valid_to = now
                invalidated = True
        if invalidated:
            self.save_ledger()
        return invalidated

    def query_as_of(self, timestamp: float) -> List[TemporalEdge]:
        """
        Query graph edges active at a specific point in history (timestamp).
        """
        active_edges = []
        for edge in self._edges:
            if edge.valid_from <= timestamp:
                if edge.valid_to is None or edge.valid_to > timestamp:
                    active_edges.append(edge)
        return active_edges

    def get_entity_history(self, entity_id: str) -> List[TemporalEdge]:
        """Retrieve complete timeline of edges associated with an entity ID."""
        return [
            edge for edge in self._edges
            if edge.source_id == entity_id or edge.target_id == entity_id
        ]


_global_temporal_kg: Optional[TemporalKnowledgeGraph] = None


def get_temporal_kg() -> TemporalKnowledgeGraph:
    global _global_temporal_kg
    if _global_temporal_kg is None:
        _global_temporal_kg = TemporalKnowledgeGraph()
    return _global_temporal_kg
