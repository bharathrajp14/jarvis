# router/__init__.py — JARVIS Unified Smart Router Package
"""
Re-exports SmartModelRouter, TaskProfile, ModelSelection, and AgentRouter envelopes.
"""

from __future__ import annotations

import sys

if __name__ in sys.modules:
    sys.modules.setdefault("router", sys.modules[__name__])

from .core import (
    ROUTING_RULES,
    AgentProfile,
    AgentRouter,
    PrivacyMode,
    get_router,
    load_available_backends,
)
from .smart_router import (
    ModelSelection,
    SmartModelRouter,
    get_smart_router,
)
from .task_profile import (
    TaskComplexity,
    TaskProfile,
    TaskProfileClassifier,
)

__all__ = [
    "TaskComplexity",
    "TaskProfile",
    "TaskProfileClassifier",
    "ModelSelection",
    "SmartModelRouter",
    "get_smart_router",
    "AgentRouter",
    "AgentProfile",
    "PrivacyMode",
    "ROUTING_RULES",
    "load_available_backends",
    "get_router",
]
