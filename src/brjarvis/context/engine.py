# context/engine.py — Core Context Engine Coordinator for JARVIS MK37
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Optional

from brjarvis.core.runtime import get_runtime
from brjarvis.events.bus import get_event_bus

from .builder import ContextBuilder
from .types import AssembledContext, ContextItem, ContextScope, TokenBudget

if TYPE_CHECKING:
    from brjarvis.router.core import AgentProfile

logger = logging.getLogger("JARVIS.ContextEngine")


class ContextEngine:
    """Master Context Engine managing system prompt generation and token-efficient context construction."""

    def __init__(self, default_budget: Optional[TokenBudget] = None):
        self.default_budget: TokenBudget = default_budget or TokenBudget()
        self.runtime = get_runtime()
        self.event_bus = get_event_bus()

        # Register self in DI container
        self.runtime.container.register_instance(ContextEngine, self)
        logger.info("⚡ ContextEngine initialized")

    def create_builder(
        self,
        max_tokens: Optional[int] = None,
        profile: Optional["AgentProfile"] = None,
    ) -> ContextBuilder:
        """Create a ContextBuilder with optional token budget or profile override."""
        if profile is not None:
            profile_str = profile.value if hasattr(profile, "value") else str(profile)
            budget = TokenBudget.from_profile(profile_str)
            if max_tokens is not None:
                budget = TokenBudget(
                    max_tokens=max_tokens,
                    reserve_response_tokens=budget.reserve_response_tokens,
                )
        elif max_tokens is not None:
            budget = TokenBudget(max_tokens=max_tokens)
        else:
            budget = self.default_budget
        return ContextBuilder(budget=budget)

    def assemble_system_context(
        self,
        conversation_history: Optional[list] = None,
        active_goal: Optional[str] = None,
        max_tokens: Optional[int] = None,
        profile: Optional["AgentProfile"] = None,
    ) -> AssembledContext:
        """Convenience method to construct full system context payload."""
        builder = self.create_builder(max_tokens=max_tokens, profile=profile)

        # 1. System Health & Hardware State
        report = self.runtime.health.generate_report()
        sys_info = (
            f"Assistant: {self.runtime.config.assistant.name} | "
            f"CPU: {report.hardware.cpu_percent:.1f}% | "
            f"RAM: {report.hardware.memory_used_percent:.1f}% | "
            f"Status: {report.overall_status}"
        )
        builder.add_item(
            ContextItem(
                scope=ContextScope.SYSTEM_STATE,
                title="System Environment",
                content=sys_info,
                priority=10,
            )
        )

        # 2. Active Goal Context
        if active_goal:
            builder.add_item(
                ContextItem(
                    scope=ContextScope.CONVERSATION,
                    title="Active Task Goal",
                    content=active_goal,
                    priority=9,
                )
            )

        # 3. Conversation History
        # FIXED: Use dynamic turn count derived from available budget, not hardcoded 6
        if conversation_history:
            budget = builder.budget
            available = budget.available_context_tokens
            # Rough estimate: ~200 tokens per turn → fit as many as budget allows
            max_turns = max(4, min(20, available // 200))
            recent_turns = conversation_history[-max_turns:]
            conv_str = "\n".join(f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent_turns)
            builder.add_item(
                ContextItem(
                    scope=ContextScope.CONVERSATION,
                    title="Recent Conversation History",
                    content=conv_str,
                    priority=8,
                )
            )

        return builder.assemble()


# ── Thread-safe singleton ─────────────────────────────────────────────────────
_global_context_engine: Optional[ContextEngine] = None
_engine_lock = threading.Lock()


def get_context_engine() -> ContextEngine:
    """Return the global ContextEngine singleton (thread-safe)."""
    global _global_context_engine
    if _global_context_engine is not None:
        return _global_context_engine
    with _engine_lock:
        if _global_context_engine is None:
            _global_context_engine = ContextEngine()
    return _global_context_engine
