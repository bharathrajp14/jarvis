# reasoning/speculative_engine.py — Backward-Compatibility Re-Export Shim
"""
This module is kept for backward compatibility only.
All canonical implementations now live in ``reasoning.speculative``.

Import from there directly:
    from brjarvis.reasoning.speculative import SpeculativeEngine, get_speculative_engine
"""
from __future__ import annotations

from brjarvis.reasoning.speculative import (  # noqa: F401
    SpeculativeEngine,
    SpeculativeDraftStep,
    SpeculativeExecutionEngine,
    get_speculative_engine,
)

__all__ = [
    "SpeculativeEngine",
    "SpeculativeDraftStep",
    "SpeculativeExecutionEngine",
    "get_speculative_engine",
]
