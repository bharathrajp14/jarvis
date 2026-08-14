# router/__init__.py — JARVIS Unified Smart Router Package
"""
Re-exports SmartModelRouter, TaskProfile, ModelSelection, and AgentRouter envelopes.
"""
from __future__ import annotations

from router.task_profile import (
    TaskComplexity,
    TaskProfile,
    TaskProfileClassifier,
)
from router.smart_router import (
    ModelSelection,
    SmartModelRouter,
    get_smart_router,
)
from router.core import (
    AgentProfile,
    AgentRouter,
    PrivacyMode,
    ROUTING_RULES,
    get_router,
    load_available_backends,
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
