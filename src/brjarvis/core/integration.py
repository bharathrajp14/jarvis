# core/integration.py — Bridge Layer between Legacy and New Subsystems in BR JARVIS
from __future__ import annotations

import logging
from typing import Optional
from .runtime import get_runtime
from events.bus import get_event_bus
from orchestrator import JarvisOrchestrator
from router import AgentRouter

logger = logging.getLogger("JARVIS.Integration")


class IntegrationBridge:
    """Manages integration bindings between new core subsystems and legacy components."""

    def __init__(self):
        self.runtime = get_runtime()
        self.event_bus = get_event_bus()
        logger.info("⚡ IntegrationBridge initialized")

    def get_orchestrator(self) -> Optional[JarvisOrchestrator]:
        """Resolve JarvisOrchestrator from DI container."""
        try:
            return self.runtime.container.resolve(JarvisOrchestrator)
        except Exception:
            return None

    def get_router(self) -> Optional[AgentRouter]:
        """Resolve AgentRouter from DI container."""
        try:
            return self.runtime.container.resolve(AgentRouter)
        except Exception:
            return None

    def publish_system_notification(self, message: str, payload: Optional[dict] = None) -> None:
        """Helper to publish system notification events from legacy components."""
        from events.types import SystemEvent
        event = SystemEvent(
            topic="system.notification",
            state="INFO",
            payload={"message": message, **(payload or {})}
        )
        self.event_bus.publish(event)


_global_bridge: Optional[IntegrationBridge] = None


def get_integration_bridge() -> IntegrationBridge:
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = IntegrationBridge()
    return _global_bridge
