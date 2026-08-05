# core/runtime.py — Core Runtime Coordinator for JARVIS MK37
from __future__ import annotations

import logging
import threading
from typing import Optional

from core.config import JarvisConfig, get_config
from core.di import Container, get_container
from core.health import HealthMonitor
from core.lifecycle import LifecycleManager
from core.logging import setup_logger
from core.process import ProcessSupervisor


class CoreRuntime:
    """Unified Core Runtime Coordinator for JARVIS MK37 Local AI OS."""

    def __init__(self, config: Optional[JarvisConfig] = None):
        self.config: JarvisConfig = config or get_config()
        self.logger: logging.Logger = setup_logger(
            name="JARVIS",
            level=self.config.system.log_level,
            log_to_file=True,
        )
        self.container: Container = get_container()
        self.lifecycle: LifecycleManager = LifecycleManager()
        self.supervisor: ProcessSupervisor = ProcessSupervisor()
        self.health: HealthMonitor = HealthMonitor()

        # Register self and core components in the DI container
        self.container.register_instance(CoreRuntime, self)
        self.container.register_instance(JarvisConfig, self.config)
        self.container.register_instance(LifecycleManager, self.lifecycle)
        self.container.register_instance(ProcessSupervisor, self.supervisor)
        self.container.register_instance(HealthMonitor, self.health)

        self.logger.info(
            f"🧠 CoreRuntime Initialized for '{self.config.assistant.name}' "
            f"(Env: {self.config.system.environment})"
        )

    async def boot(self) -> None:
        """Boot the Core Runtime and all registered startup tasks.

        Must be called from within a running asyncio event loop.
        """
        await self.lifecycle.startup()

    async def shutdown(self) -> None:
        """Shutdown the Core Runtime cleanly.

        Must be called from within a running asyncio event loop.
        """
        await self.lifecycle.shutdown()


# ── Thread-safe singleton ─────────────────────────────────────────────────────
_global_runtime: Optional[CoreRuntime] = None
_runtime_lock = threading.Lock()


def get_runtime() -> CoreRuntime:
    """Return the global CoreRuntime singleton (thread-safe).

    Uses double-checked locking to prevent duplicate initialization when called
    simultaneously from multiple threads (e.g., voice thread + server lifespan).
    """
    global _global_runtime

    # Fast path — no lock needed for reading an immutable reference
    if _global_runtime is not None:
        return _global_runtime

    with _runtime_lock:
        # Double-checked locking: verify again inside the lock
        if _global_runtime is None:
            _global_runtime = CoreRuntime()
    return _global_runtime


def reset_runtime() -> None:
    """Reset the global runtime singleton (for testing only)."""
    global _global_runtime
    with _runtime_lock:
        _global_runtime = None
