# reasoning/meta_cognition.py — Meta-Cognition & Self-Evaluation Engine for BR JARVIS MK38
"""
Pre-execution meta-cognitive evaluation layer predicting execution risk, CoT depth,
context completeness, and goal feasibility before dispatching tool calls.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from brjarvis.core.runtime import get_runtime

logger = logging.getLogger("JARVIS.MetaCognition")


class MetaCognitiveAssessment(BaseModel):
    """Structured assessment payload produced before goal execution."""

    goal: str
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Estimated feasibility (0.0 to 1.0)")
    reasoning_depth: int = Field(default=1, description="Recommended CoT step depth")
    perceived_risk: str = Field(default="LOW", description="LOW, MEDIUM, HIGH, or CRITICAL")
    missing_context: List[str] = Field(default_factory=list, description="Dependencies or context missing")
    alternative_strategies: List[str] = Field(default_factory=list, description="Alternative execution paths")
    suggested_action: str = Field(default="PROCEED", description="PROCEED, RE-PLAN, CLARIFY, or ABORT")
    evaluated_at: float = Field(default_factory=time.time)


class MetaCognitionEngine:
    """
    Evaluates goal execution feasibility, context sufficiency, and historical failure risks.
    """

    def __init__(self, confidence_threshold: float = 0.70):
        self.confidence_threshold = confidence_threshold
        self.runtime = get_runtime()
        self.runtime.container.register_instance(MetaCognitionEngine, self)
        logger.info(f"⚡ MetaCognitionEngine initialized (threshold: {confidence_threshold})")

    def evaluate_intent(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        historical_failures: Optional[List[Dict[str, Any]]] = None,
    ) -> MetaCognitiveAssessment:
        """
        Evaluate a user goal against context and historical failure trajectory memory.
        """
        logger.info(f"🧠 MetaCognition: Evaluating feasibility for goal: '{goal[:60]}...'")

        goal_lower = goal.lower()
        context = context or {}
        historical_failures = historical_failures or []

        # 1. Base confidence calculation
        confidence = 0.90
        missing = []
        alternatives = []
        risk = "LOW"
        suggested_action = "PROCEED"

        # 2. Check for missing critical context
        if "file" in goal_lower or "read" in goal_lower or "edit" in goal_lower:
            if (
                not context.get("active_file")
                and not context.get("target_file")
                and not any(ext in goal_lower for ext in [".py", ".md", ".json", ".txt", ".js", ".ts", ".html"])
            ):
                missing.append("Target file path ambiguous")
                confidence -= 0.15

        # 3. Check for high-risk operations (system mutations)
        high_risk_keywords = ["delete", "remove", "drop database", "format", "rm -rf", "git push --force"]
        if any(kw in goal_lower for kw in high_risk_keywords):
            risk = "HIGH"
            confidence -= 0.25
            missing.append("Explicit confirmation for destructive operation")

        # 4. Evaluate against historical failure patterns
        for failure in historical_failures:
            fail_reason = str(failure.get("failure_reason", "")).lower()
            fail_goal = str(failure.get("goal_query", "")).lower()
            if fail_goal and fail_goal in goal_lower:
                confidence -= 0.20
                alternatives.append(f"Avoid previous failed approach: {fail_reason[:50]}")

        # Clamp confidence score to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))

        # 5. Determine suggested action based on thresholds
        if confidence < self.confidence_threshold:
            if risk in ("HIGH", "CRITICAL"):
                suggested_action = "CLARIFY"
            else:
                suggested_action = "RE-PLAN"
                alternatives.append("Decompose goal into smaller sub-tasks")

        assessment = MetaCognitiveAssessment(
            goal=goal,
            confidence_score=round(confidence, 2),
            reasoning_depth=2 if confidence < 0.85 else 1,
            perceived_risk=risk,
            missing_context=missing,
            alternative_strategies=alternatives,
            suggested_action=suggested_action,
        )

        logger.info(
            f"✨ MetaCognition Assessment: Action={assessment.suggested_action}, Confidence={assessment.confidence_score}, Risk={assessment.perceived_risk}"
        )
        return assessment


_global_meta_cognition: Optional[MetaCognitionEngine] = None


def get_meta_cognition() -> MetaCognitionEngine:
    global _global_meta_cognition
    if _global_meta_cognition is None:
        _global_meta_cognition = MetaCognitionEngine()
    return _global_meta_cognition
