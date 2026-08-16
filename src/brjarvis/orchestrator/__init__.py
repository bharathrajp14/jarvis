# orchestrator/__init__.py — JARVIS MK37 Orchestrator Package
"""
Re-exports JarvisOrchestrator and speculative components for unified import.
"""
from __future__ import annotations

from .core import JarvisOrchestrator, MODES, SYSTEM_PROMPT

__all__ = [
    "JarvisOrchestrator",
    "MODES",
    "SYSTEM_PROMPT",
]
