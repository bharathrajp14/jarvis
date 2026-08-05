from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from core.runtime import CoreRuntime, get_runtime
from events.bus import EventBus, get_event_bus
from events.types import SystemEvent
from orchestrator import JarvisOrchestrator
from router import AgentRouter, load_available_backends


@dataclass(slots=True)
class AssistantRuntime:
    backends: dict
    router: AgentRouter
    orchestrator: JarvisOrchestrator
    core_runtime: Optional[CoreRuntime] = None
    event_bus: Optional[EventBus] = None


# ── Singleton Guard ──────────────────────────────────────────────────────────
_runtime_instance: AssistantRuntime | None = None
_runtime_lock = threading.Lock()


def build_assistant_runtime(*, use_vector_memory: bool = True) -> AssistantRuntime:
    """Create or return the shared singleton backend/router/orchestrator stack.

    Thread-safe: multiple entry points (voice thread, server lifespan, CLI)
    will all receive the same AssistantRuntime instance, preventing duplicate
    backend connections, split working memory, and invisible event buses.
    """
    global _runtime_instance

    # Fast path — already built (no lock needed for read of immutable ref)
    if _runtime_instance is not None:
        return _runtime_instance

    with _runtime_lock:
        # Double-checked locking
        if _runtime_instance is not None:
            return _runtime_instance

        core_runtime = get_runtime()
        event_bus = get_event_bus()

        backends = load_available_backends()
        router = AgentRouter(backends)
        orchestrator = JarvisOrchestrator(router, use_vector_memory=use_vector_memory)

        # Register components in DI container
        core_runtime.container.register_instance(AgentRouter, router)
        core_runtime.container.register_instance(JarvisOrchestrator, orchestrator)
        core_runtime.container.register_instance(EventBus, event_bus)

        # FIXED: Register orchestrator shutdown hook so memory is consolidated
        # on graceful shutdown, not abandoned silently.
        async def _orchestrator_shutdown():
            try:
                orchestrator.shutdown()
            except Exception:
                pass

        core_runtime.lifecycle.add_shutdown_hook(_orchestrator_shutdown)

        # FIXED: Publish startup event AFTER all DI registrations are complete
        # so any subscriber that gets added during registration sees this event.
        event_bus.publish(SystemEvent(
            topic="system.startup",
            state="RUNNING",
            payload={"backends_count": len(backends)}
        ))

        _runtime_instance = AssistantRuntime(
            backends=backends,
            router=router,
            orchestrator=orchestrator,
            core_runtime=core_runtime,
            event_bus=event_bus,
        )
        return _runtime_instance


def reset_assistant_runtime() -> None:
    """Reset the singleton (for testing only)."""
    global _runtime_instance
    with _runtime_lock:
        _runtime_instance = None
