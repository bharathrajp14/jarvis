# reasoning/cognitive_loop.py — Closed-Loop Cognitive Cycle & Verification Engine
"""
Implements explicit Observe -> Think -> Critic -> Improve -> Retry cognitive loop
for BR JARVIS step execution evaluation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS.CognitiveLoop")


class SelfEvaluationPayload(BaseModel):
    """Structured internal self-evaluation metric generated during cognitive reflection."""

    step_id: int | str
    goal_snippet: str
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence metric (0.0 - 1.0)")
    reasoning_depth: int = Field(default=1, description="Depth of CoT reasoning steps")
    missing_info: List[str] = Field(default_factory=list, description="Identified missing context or dependencies")
    alternative_options: List[str] = Field(
        default_factory=list, description="Alternative execution pathways considered"
    )
    failure_risk: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Estimated probability of step execution failure"
    )
    should_retry: bool = False
    improvement_suggestion: Optional[str] = None


class CognitiveLoop:
    """
    Closed-loop cognitive cycle manager coordinating the observe-think-critic-improve execution loop.
    """

    def __init__(self):
        self.history: List[SelfEvaluationPayload] = []

    def evaluate_step_outcome(
        self,
        step_id: int | str,
        goal: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_output: str,
        execution_success: bool,
    ) -> SelfEvaluationPayload:
        """
        Evaluate tool execution outcome and produce a SelfEvaluationPayload.
        """
        lower_output = str(tool_output).lower()

        # Check for failure indicators
        failure_signals = ["error", "exception", "failed", "permission denied", "not found", "timeout", "invalid"]
        has_failure_signal = any(sig in lower_output for sig in failure_signals) or not execution_success

        if has_failure_signal:
            confidence = 0.2 if not execution_success else 0.4
            failure_risk = 0.8
            should_retry = True
            improvement = f"Adapt tool choice or parameters for '{tool_name}'. Previous execution encountered errors."
        else:
            confidence = 0.95
            failure_risk = 0.05
            should_retry = False
            improvement = None

        evaluation = SelfEvaluationPayload(
            step_id=step_id,
            goal_snippet=goal[:80],
            confidence_score=confidence,
            reasoning_depth=2,
            missing_info=[] if execution_success else ["Tool execution error output"],
            alternative_options=["fallback_script", "python_code_execution"],
            failure_risk=failure_risk,
            should_retry=should_retry,
            improvement_suggestion=improvement,
        )

        self.history.append(evaluation)
        logger.info(f"🧠 CognitiveLoop: Step {step_id} evaluated with confidence {evaluation.confidence_score:.2f}")
        return evaluation


_global_cognitive_loop: Optional[CognitiveLoop] = None


def get_cognitive_loop() -> CognitiveLoop:
    """Singleton getter for CognitiveLoop."""
    global _global_cognitive_loop
    if _global_cognitive_loop is None:
        _global_cognitive_loop = CognitiveLoop()
    return _global_cognitive_loop
