# orchestrator/speculative.py — Backward-Compatibility Re-Export Shim — BR JARVIS v41.0
"""
Re-exports the canonical speculative execution classes from ``reasoning.speculative``.
Import directly from there when writing new code.
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
