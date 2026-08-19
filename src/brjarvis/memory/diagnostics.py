# memory/diagnostics.py — Observability, Debug Tracing & User Memory Controls
"""
Observability, Diagnostic Tracing, and User Memory Controls for BR JARVIS.
Provides:
- `/debug memory <query>`: Full retrieval pipeline diagnostic trace (classification, scores, conflicts, ranking, injected prompt)
- `/debug decision <id>`: Structured decision tree, alternatives, risk, and receipts
- Safe task replay from Execution Ledger without re-executing side effects
- User memory control operations (remember, forget, show, correct, invalidate, export)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from brjarvis.agent.execution_ledger import get_execution_ledger
from brjarvis.reasoning.decision_engine import get_decision_engine

from .domain import CanonicalMemory
from .retrieval import RankedMemoryCandidate, get_retrieval_engine
from .store import get_canonical_store
from .task_memory_router import get_task_memory_router
from .temporal import get_temporal_engine
from .unified_memory import get_unified_memory

logger = logging.getLogger("JARVIS.MemoryDiagnostics")


class MemoryDiagnostics:
    """Comprehensive observability and diagnostics controller for agent memory and decisions."""

    def __init__(self):
        self.store = get_canonical_store()
        self.retrieval = get_retrieval_engine()
        self.router = get_task_memory_router()
        self.temporal = get_temporal_engine()
        self.decisions = get_decision_engine()
        self.ledger = get_execution_ledger()
        self.unified = get_unified_memory()

    def debug_memory(self, query: str, project_id: str = "global") -> Dict[str, Any]:
        """
        Execute full diagnostic trace of memory retrieval for a query.
        Returns all candidate memories, similarity scores, ranking factors, conflicts,
        and the final injected context block.
        """
        start_t = time.perf_counter()

        # 1. Classification
        classification = self.router.classify(query)

        # 2. Hybrid Search & Ranking
        ranked_hits: List[RankedMemoryCandidate] = self.retrieval.search(
            query=query,
            project_id=project_id,
            limit=10,
            min_score=0.10,
        )

        candidates_data = [h.to_dict() for h in ranked_hits]
        selected = [h for h in ranked_hits if h.final_score >= 0.25][:5]
        rejected = [h for h in ranked_hits if h not in selected]

        # 3. Format injection block
        slices_for_injection = [
            {
                "name": h.memory.entity or h.memory.attribute or "Memory",
                "content": h.memory.content,
                "memory_type": h.memory.memory_type.value,
                "selection_reason": h.selection_reason,
            }
            for h in selected
        ]
        injected_context = self.router.format_memory_injection(slices_for_injection, classification)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        return {
            "query": query,
            "project_id": project_id,
            "latency_ms": round(elapsed_ms, 2),
            "classification": classification.value.upper(),
            "total_candidates_found": len(ranked_hits),
            "selected_memories_count": len(selected),
            "selected_memories": [s.to_dict() for s in selected],
            "rejected_memories": [r.to_dict() for r in rejected],
            "final_injected_context": injected_context,
        }

    def debug_decision(self, task_id_or_decision_id: str) -> Dict[str, Any]:
        """Retrieve and format complete decision receipt and audit trail."""
        dec = self.decisions.get_decision(task_id_or_decision_id)
        if dec:
            return {
                "decision_id": dec.decision_id,
                "task_id": dec.task_id,
                "question": dec.question,
                "goal": dec.goal,
                "selected_option": dec.selected_option,
                "rejected_options": dec.rejected_options,
                "evidence": dec.evidence,
                "constraints": dec.constraints,
                "risk_level": dec.risk_level,
                "confidence": dec.confidence,
                "expected_outcome": dec.expected_outcome,
                "verification_plan": dec.verification_plan,
                "reversible": dec.reversible,
                "status": dec.status,
                "actual_outcome": dec.actual_outcome,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dec.created_at)),
            }

        task_decs = self.decisions.list_task_decisions(task_id_or_decision_id)
        return {
            "task_id": task_id_or_decision_id,
            "decisions_count": len(task_decs),
            "decisions": [d.to_receipt() for d in task_decs],
        }

    def replay_task(self, task_id: str) -> Dict[str, Any]:
        """Reconstruct full task trajectory from immutable Execution Ledger without executing side effects."""
        entries = self.ledger.get_task_entries(task_id)
        task_decs = self.decisions.list_task_decisions(task_id)

        steps = []
        for e in entries:
            steps.append(
                {
                    "step_id": e.step_id,
                    "tool_name": e.tool_name,
                    "status": e.status.value,
                    "duration_seconds": e.duration_seconds,
                    "evidence": e.evidence,
                    "side_effects": e.side_effects,
                    "error": e.error,
                    "verification_status": e.verification_status.value,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.timestamp)),
                }
            )

        return {
            "task_id": task_id,
            "total_steps_executed": len(steps),
            "has_critical_failure": self.ledger.task_has_critical_failure(task_id),
            "decisions": [d.to_receipt() for d in task_decs],
            "execution_steps": steps,
            "evidence_report": self.ledger.build_evidence_report(task_id),
        }

    # ── User Memory Controls ──────────────────────────────────────────────────

    def remember(self, key: str, value: str, scope: str = "user", project_id: str = "global") -> CanonicalMemory:
        return self.unified.remember(
            name=key, content=f"{key} = {value}", value=value, entity=key, scope=scope, project_id=project_id
        )

    def forget(self, key: str, scope: str = "user") -> bool:
        return self.unified.forget(key, scope=scope)

    def correct(self, key: str, new_value: str, reason: str = "") -> CanonicalMemory:
        return self.unified.correct(entity=key, attribute=key, new_value=new_value, reason=reason)

    def show_memory(self, user_id: str = "default_user", project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        mems = self.store.list_active(user_id=user_id, project_id=project_id)
        return [m.to_dict() for m in mems]

    def export_memory(self, user_id: str = "default_user") -> str:
        mems = self.store.list_all(user_id=user_id)
        return json.dumps([m.to_dict() for m in mems], indent=2)

    def delete_all_memory(self, user_id: str = "default_user") -> int:
        return self.store.delete_all(user_id=user_id)


_GLOBAL_DIAGNOSTICS: Optional[MemoryDiagnostics] = None


def get_memory_diagnostics() -> MemoryDiagnostics:
    global _GLOBAL_DIAGNOSTICS
    if _GLOBAL_DIAGNOSTICS is None:
        _GLOBAL_DIAGNOSTICS = MemoryDiagnostics()
    return _GLOBAL_DIAGNOSTICS
