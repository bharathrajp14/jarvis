# evolution/classifier.py — Blast-Radius Risk Classifier
"""
Classifies candidate code or configuration patches by blast-radius risk level:
- LOW: Auto-applies on passing tests (tools, skills, prompts, routing weights).
- MEDIUM: Auto-applies with 24h undo window and pre-deploy snapshot (context, memory, heuristics).
- HIGH: Queued for human approval (guardian, permissions, safety checks, credentials).
"""
from __future__ import annotations

import enum
from pathlib import Path


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


HIGH_RISK_PATHS = frozenset({
    "guardian/core.py",
    "guardian/kill_switch.py",
    "guardian/snapshot.py",
    "guardian/rollback.py",
    "guardian/audit_log.py",
    "permissions.py",
    "computer/operator.py",
    "backends/base.py",
})


MEDIUM_RISK_PATHS = frozenset({
    "context/builder.py",
    "context/compressor.py",
    "context/engine.py",
    "memory/unified_memory.py",
    "agent/planner.py",
    "router.py",
})


class ChangeClassifier:
    """Classifies proposed patch files into LOW, MEDIUM, or HIGH risk categories."""

    @classmethod
    def classify_patch(cls, target_files: list[str]) -> RiskLevel:
        """Classify blast radius of a patch affecting a list of target file paths."""
        highest_risk = RiskLevel.LOW

        for f in target_files:
            clean_f = str(Path(f)).replace("\\", "/").lower()

            # Check HIGH risk
            if any(h in clean_f for h in HIGH_RISK_PATHS):
                return RiskLevel.HIGH

            # Check MEDIUM risk
            if any(m in clean_f for m in MEDIUM_RISK_PATHS):
                highest_risk = RiskLevel.MEDIUM

        return highest_risk
