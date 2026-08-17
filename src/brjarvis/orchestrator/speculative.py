# orchestrator/speculative.py — Speculative Drafting & Execution Engine for BR JARVIS MK38
"""
Implements speculative drafting and parallel validation to accelerate tool step execution loops.
Re-exports from reasoning.speculative for seamless import compatibility.
"""
from __future__ import annotations

from brjarvis.reasoning.speculative import (
    SpeculativeDraftStep,
    SpeculativeExecutionEngine,
    get_speculative_engine,
)

__all__ = [
    "SpeculativeDraftStep",
    "SpeculativeExecutionEngine",
    "get_speculative_engine",
]
