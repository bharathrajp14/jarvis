# reasoning/decision_engine.py — Decision Subsystem & Traceable Decision Receipts
"""
Authoritative Decision Subsystem for BR JARVIS.
Captures structured decision receipts containing:
- Goal, Question, Options, Selection, and Rejected Alternatives
- Supporting Evidence & Active Constraints
- Risk Level, Confidence, and Reversibility
- Verification Plan and Actual Outcome
Provides programmatic consistency validation before executing meaningful actions.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from brjarvis.memory.canonical_db import CanonicalDatabaseManager, get_canonical_db

logger = logging.getLogger("JARVIS.DecisionEngine")


@dataclass
class Decision:
    """A first-class machine-readable decision record."""
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:10]}")
    task_id: str = ""
    question: str = ""
    goal: str = ""
    options: List[str] = field(default_factory=list)
    selected_option: str = ""
    rejected_options: List[str] = field(default_factory=list)
    evidence: str = ""
    constraints: List[str] = field(default_factory=list)
    risk_level: str = "low"            # "low" | "medium" | "high" | "critical"
    confidence: float = 1.0            # 0.0 to 1.0
    expected_outcome: str = ""
    verification_plan: str = ""
    reversible: bool = True
    approval_required: bool = False
    status: str = "ACTIVE"             # "ACTIVE" | "SUPERSEDED" | "INVALIDATED"
    actual_outcome: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_receipt(self) -> Dict[str, Any]:
        """Generate machine-readable decision receipt for audit and downstream execution."""
        return {
            "decision_id": self.decision_id,
            "task_id": self.task_id,
            "question": self.question,
            "goal": self.goal,
            "selected_option": self.selected_option,
            "rejected_options": self.rejected_options,
            "evidence": self.evidence,
            "constraints": self.constraints,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "verification_plan": self.verification_plan,
            "reversible": self.reversible,
            "status": self.status,
            "created_at": self.created_at,
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DecisionEngine:
    """Manages recording, validation, consistency checks, and invalidation of agent decisions."""

    def __init__(self, db_manager: Optional[CanonicalDatabaseManager] = None):
        self.db = db_manager or get_canonical_db()

    def record_decision(
        self,
        question: str,
        goal: str,
        selected_option: str,
        rejected_options: Optional[List[str]] = None,
        task_id: str = "",
        evidence: str = "",
        constraints: Optional[List[str]] = None,
        risk_level: str = "low",
        confidence: float = 1.0,
        expected_outcome: str = "",
        verification_plan: str = "",
        reversible: bool = True,
        approval_required: bool = False,
    ) -> Decision:
        """Create and persist a structured decision in canonical database."""
        options = [selected_option] + (rejected_options or [])
        dec = Decision(
            task_id=task_id,
            question=question,
            goal=goal,
            options=options,
            selected_option=selected_option,
            rejected_options=rejected_options or [],
            evidence=evidence,
            constraints=constraints or [],
            risk_level=risk_level,
            confidence=confidence,
            expected_outcome=expected_outcome,
            verification_plan=verification_plan,
            reversible=reversible,
            approval_required=approval_required,
        )

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO decisions (
                    decision_id, task_id, question, goal, options_json, selected_option,
                    rejected_options_json, evidence, constraints_json, risk_level,
                    confidence, expected_outcome, verification_plan, reversible,
                    approval_required, status, actual_outcome, receipt_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dec.decision_id, dec.task_id, dec.question, dec.goal,
                    json.dumps(dec.options), dec.selected_option,
                    json.dumps(dec.rejected_options), dec.evidence,
                    json.dumps(dec.constraints), dec.risk_level, dec.confidence,
                    dec.expected_outcome, dec.verification_plan, 1 if dec.reversible else 0,
                    1 if dec.approval_required else 0, dec.status, dec.actual_outcome,
                    json.dumps(dec.to_receipt()), dec.created_at, dec.updated_at,
                ),
            )
            conn.commit()

        logger.info(f"⚖️ Decision recorded: [{dec.decision_id}] {dec.question} -> {dec.selected_option} (Risk: {dec.risk_level})")
        return dec

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Fetch decision by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decisions WHERE decision_id = ?", (decision_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_decision(row)

    def list_task_decisions(self, task_id: str) -> List[Decision]:
        """Retrieve all decisions made under a specific task."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decisions WHERE task_id = ? ORDER BY created_at ASC", (task_id,))
            return [self._row_to_decision(row) for row in cursor.fetchall()]

    def validate_action_against_decisions(
        self,
        action_description: str,
        task_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if a proposed action contradicts any active decisions or constraints.
        Returns: (is_valid, violation_reason)
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if task_id:
                cursor.execute(
                    "SELECT * FROM decisions WHERE task_id = ? AND status = 'ACTIVE'",
                    (task_id,),
                )
            else:
                cursor.execute(
                    "SELECT * FROM decisions WHERE status = 'ACTIVE' ORDER BY created_at DESC LIMIT 20"
                )
            rows = cursor.fetchall()

        act_lower = action_description.lower()
        for row in rows:
            dec = self._row_to_decision(row)
            # Check if action attempts a previously rejected option
            for rej in dec.rejected_options:
                if rej.lower() in act_lower and len(rej.strip()) > 3:
                    return False, f"Action conflicts with Decision {dec.decision_id}: '{rej}' was explicitly rejected ({dec.evidence})."

        return True, None

    def invalidate_decision(self, decision_id: str, reason: str = "") -> bool:
        """Mark an outdated or disproven decision as INVALIDATED."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE decisions SET status = 'INVALIDATED', updated_at = ? WHERE decision_id = ?",
                (time.time(), decision_id),
            )
            conn.commit()
            logger.info(f"🚫 Decision invalidated: {decision_id} (Reason: {reason})")
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_decision(row: Any) -> Decision:
        return Decision(
            decision_id=row["decision_id"],
            task_id=row["task_id"] or "",
            question=row["question"],
            goal=row["goal"],
            options=json.loads(row["options_json"] or "[]"),
            selected_option=row["selected_option"],
            rejected_options=json.loads(row["rejected_options_json"] or "[]"),
            evidence=row["evidence"] or "",
            constraints=json.loads(row["constraints_json"] or "[]"),
            risk_level=row["risk_level"] or "low",
            confidence=float(row["confidence"]),
            expected_outcome=row["expected_outcome"] or "",
            verification_plan=row["verification_plan"] or "",
            reversible=bool(row["reversible"]),
            approval_required=bool(row["approval_required"]),
            status=row["status"],
            actual_outcome=row["actual_outcome"],
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )


_GLOBAL_DECISION_ENGINE: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Return singleton DecisionEngine."""
    global _GLOBAL_DECISION_ENGINE
    if _GLOBAL_DECISION_ENGINE is None:
        _GLOBAL_DECISION_ENGINE = DecisionEngine()
    return _GLOBAL_DECISION_ENGINE
