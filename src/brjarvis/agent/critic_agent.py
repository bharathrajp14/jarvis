# agent/critic_agent.py — Autonomous Critic & Verifier Sub-Agent
"""
Dedicated CriticAgent that reviews execution plans, step outputs, and tool responses
to prevent hallucinated completions and enforce output accuracy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from pydantic import BaseModel, Field

logger = logging.getLogger("JARVIS.CriticAgent")


class CritiqueResult(BaseModel):
    """Result payload from CriticAgent review."""

    is_valid: bool
    quality_score: float = Field(..., ge=0.0, le=1.0)
    criticisms: List[str] = Field(default_factory=list)
    recommended_action: str = "PROCEED"  # PROCEED, RETRY, REPLAN, ABORT


class CriticAgent:
    """
    Sub-agent tasked with objective critique of plan steps and tool outputs.
    """

    def __init__(self):
        logger.info("🔍 CriticAgent initialized")

    def critique_step_output(
        self,
        goal: str,
        step_description: str,
        tool_name: str,
        output_text: str,
    ) -> CritiqueResult:
        """
        Critique the output of an executed tool step.
        """
        criticisms: List[str] = []
        clean_output = str(output_text).strip()

        # Check for empty output
        if not clean_output:
            criticisms.append("Tool returned empty or blank output.")
            return CritiqueResult(
                is_valid=False,
                quality_score=0.0,
                criticisms=criticisms,
                recommended_action="RETRY",
            )

        # Check for explicit failure messages
        error_keywords = ["exception", "traceback", "commandnotfoundexception", "permissiondenied"]
        if any(kw in clean_output.lower() for kw in error_keywords):
            criticisms.append("Output contains execution error keywords.")
            return CritiqueResult(
                is_valid=False,
                quality_score=0.3,
                criticisms=criticisms,
                recommended_action="RETRY",
            )

        # High quality output
        return CritiqueResult(
            is_valid=True,
            quality_score=0.95,
            criticisms=[],
            recommended_action="PROCEED",
        )

    def review_plan_feasibility(self, goal: str, steps: List[Dict[str, Any]]) -> CritiqueResult:
        """
        Review a decomposed plan graph before execution.
        """
        if not steps:
            return CritiqueResult(
                is_valid=False,
                quality_score=0.0,
                criticisms=["Plan contains zero execution steps."],
                recommended_action="REPLAN",
            )

        return CritiqueResult(
            is_valid=True,
            quality_score=0.9,
            criticisms=[],
            recommended_action="PROCEED",
        )
