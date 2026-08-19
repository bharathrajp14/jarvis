# memory/temporal.py — Temporal Memory & Time-Aware Fact Engine
"""
Temporal State Engine for BR JARVIS.
Answers:
- What is true now?
- What was true before?
- When did it change?
- What changed?
- Why did it change?
- Which record superseded the previous one?
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .domain import CanonicalMemory
from .store import CanonicalMemoryStore, get_canonical_store

logger = logging.getLogger("JARVIS.TemporalEngine")


class TemporalEngine:
    """Time-aware memory engine tracking point-in-time validity and evolution."""

    def __init__(self, store: Optional[CanonicalMemoryStore] = None):
        self.store = store or get_canonical_store()

    def get_current_truth(
        self,
        entity: str,
        attribute: str,
        project_id: str = "global",
        scope: Optional[str] = None,
    ) -> Optional[CanonicalMemory]:
        """Return the memory record that represents current authoritative ground truth."""
        with self.store.db.get_connection() as conn:
            cursor = conn.cursor()
            now = time.time()
            cursor.execute(
                """
                SELECT * FROM canonical_memories
                WHERE entity = ? AND attribute = ?
                  AND (project_id = ? OR project_id = 'global')
                  AND (? IS NULL OR scope = ?)
                  AND status = 'ACTIVE'
                  AND effective_from <= ?
                  AND (effective_until IS NULL OR effective_until > ?)
                ORDER BY
                  CASE WHEN project_id = ? THEN 1 ELSE 0 END DESC,
                  CASE WHEN scope = ? THEN 1 ELSE 0 END DESC,
                  version DESC, updated_at DESC
                LIMIT 1
                """,
                (entity, attribute, project_id, scope, scope, now, now, project_id, scope),
            )
            row = cursor.fetchone()
            if row:
                return self.store._row_to_memory(row)
            return None

    def get_truth_at_timestamp(
        self,
        entity: str,
        attribute: str,
        timestamp: float,
        project_id: str = "global",
        scope: Optional[str] = None,
    ) -> Optional[CanonicalMemory]:
        """Return what fact was active and authoritative at an exact point in historical time."""
        with self.store.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM canonical_memories
                WHERE entity = ? AND attribute = ?
                  AND (project_id = ? OR project_id = 'global')
                  AND (? IS NULL OR scope = ?)
                  AND status IN ('ACTIVE', 'SUPERSEDED')
                  AND effective_from <= ?
                  AND (effective_until IS NULL OR effective_until > ?)
                ORDER BY
                  CASE WHEN project_id = ? THEN 1 ELSE 0 END DESC,
                  CASE WHEN scope = ? THEN 1 ELSE 0 END DESC,
                  version DESC
                LIMIT 1
                """,
                (entity, attribute, project_id, scope, scope, timestamp, timestamp, project_id, scope),
            )
            row = cursor.fetchone()
            if row:
                return self.store._row_to_memory(row)
            return None

    def get_timeline(self, entity: str, attribute: str) -> List[Dict[str, Any]]:
        """Retrieve full chronological evolution timeline for an entity attribute."""
        records = self.store.list_history(entity, attribute)
        timeline = []
        for r in records:
            from_dt = datetime.fromtimestamp(r.effective_from).strftime("%Y-%m-%d %H:%M:%S")
            until_dt = (
                datetime.fromtimestamp(r.effective_until).strftime("%Y-%m-%d %H:%M:%S")
                if r.effective_until
                else "Present (Current)"
            )
            timeline.append(
                {
                    "memory_id": r.memory_id,
                    "version": r.version,
                    "value": r.value,
                    "content": r.content,
                    "status": r.status.value,
                    "source_type": r.source_type.value,
                    "evidence": r.evidence,
                    "valid_from": from_dt,
                    "valid_until": until_dt,
                    "effective_from_ts": r.effective_from,
                    "effective_until_ts": r.effective_until,
                    "supersedes_memory_id": r.supersedes_memory_id,
                    "superseded_by_memory_id": r.superseded_by_memory_id,
                }
            )
        return timeline

    def explain_temporal_change(self, entity: str, attribute: str) -> str:
        """Produce an explainable human/agent diagnostic breakdown of what changed over time."""
        timeline = self.get_timeline(entity, attribute)
        if not timeline:
            return f"No historical records found for '{entity}' ({attribute})."

        lines = [f"### 🕒 Temporal Evolution for `{entity}` -> `{attribute}`:"]
        for entry in timeline:
            status_emoji = "🟢 ACTIVE" if entry["status"] == "ACTIVE" else "⚪ SUPERSEDED"
            lines.append(
                f"- **v{entry['version']} [{status_emoji}]**: Value: `{entry['value']}` "
                f"(Valid: {entry['valid_from']} → {entry['valid_until']}) | "
                f"Source: {entry['source_type']}"
            )
            if entry["supersedes_memory_id"]:
                lines.append(f"  ↳ Replaced previous record `{entry['supersedes_memory_id']}`")
            if entry["evidence"]:
                lines.append(f"  ↳ Evidence: {entry['evidence']}")

        current = self.get_current_truth(entity, attribute)
        if current:
            lines.append(
                f"\n**Current Authority**: `{current.value}` (Status: {current.status.value}, v{current.version})"
            )
        return "\n".join(lines)


_GLOBAL_TEMPORAL_ENGINE: Optional[TemporalEngine] = None


def get_temporal_engine() -> TemporalEngine:
    """Return singleton TemporalEngine."""
    global _GLOBAL_TEMPORAL_ENGINE
    if _GLOBAL_TEMPORAL_ENGINE is None:
        _GLOBAL_TEMPORAL_ENGINE = TemporalEngine()
    return _GLOBAL_TEMPORAL_ENGINE
