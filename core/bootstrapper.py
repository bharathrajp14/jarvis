# core/bootstrapper.py — Unified System Bootstrapper Compatibility Shim
"""
Compatibility shim re-exporting CoreBootstrapper from core.bootstrap.
"""
from __future__ import annotations

from core.bootstrap import AssistantRuntime, CoreBootstrapper, build_assistant_runtime, reset_assistant_runtime

__all__ = [
    "AssistantRuntime",
    "CoreBootstrapper",
    "build_assistant_runtime",
    "reset_assistant_runtime",
]
