# core/lifecycle.py — Async Service Lifecycle & Signal Management for JARVIS MK37
from __future__ import annotations

import asyncio
import enum
import logging
import signal
from typing import Awaitable, Callable, List, Optional

logger = logging.getLogger("JARVIS.Lifecycle")


class SystemState(str, enum.Enum):
    UNINITIALIZED = "UNINITIALIZED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    SHUTDOWN = "SHUTDOWN"


HookCallable = Callable[[], Awaitable[None]]


class LifecycleManager:
    """Async lifecycle manager handling application boot, shutdown, and OS signal traps."""

    def __init__(self):
        self.state: SystemState = SystemState.UNINITIALIZED
        self._startup_hooks: List[HookCallable] = []
        self._shutdown_hooks: List[HookCallable] = []
        # FIXED: asyncio.Event is created lazily inside async context to avoid
        # Python 3.9 implicit-loop binding issues when created in __init__.
        self._shutdown_event: Optional[asyncio.Event] = None

    def _get_shutdown_event(self) -> asyncio.Event:
        """Lazily create the shutdown event inside an async context."""
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        return self._shutdown_event

    def add_startup_hook(self, hook: HookCallable) -> None:
        """Register an async startup task."""
        self._startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: HookCallable) -> None:
        """Register an async cleanup/shutdown task (executed in reverse order)."""
        self._shutdown_hooks.append(hook)

    async def startup(self) -> None:
        """Execute all registered startup hooks in registration order."""
        if self.state != SystemState.UNINITIALIZED:
            return
        self.state = SystemState.STARTING
        logger.info("🚀 Initiating System Startup Sequence...")

        for hook in self._startup_hooks:
            hook_name = getattr(hook, "__name__", repr(hook))
            try:
                await asyncio.wait_for(hook(), timeout=15.0)
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Startup hook '{hook_name}' timed out after 15s — continuing")
            except Exception as exc:
                logger.error(f"❌ Startup hook '{hook_name}' raised: {exc}", exc_info=True)

        self.state = SystemState.RUNNING
        logger.info("✅ System State: RUNNING")

    async def shutdown(self) -> None:
        """Execute all registered shutdown hooks in reverse registration order."""
        if self.state in (SystemState.STOPPING, SystemState.SHUTDOWN):
            return
        self.state = SystemState.STOPPING
        logger.info("🛑 Initiating Graceful System Shutdown...")

        for hook in reversed(self._shutdown_hooks):
            hook_name = getattr(hook, "__name__", repr(hook))
            try:
                await asyncio.wait_for(hook(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Shutdown hook '{hook_name}' timed out after 10s — skipping")
            except Exception as exc:
                logger.error(f"⚠️ Shutdown hook '{hook_name}' raised: {exc}")

        self.state = SystemState.SHUTDOWN
        self._get_shutdown_event().set()
        logger.info("👋 System State: SHUTDOWN complete")

    def attach_signal_handlers(self) -> None:
        """Register SIGINT and SIGTERM OS signal handlers.

        Only effective when called from within a running asyncio event loop.
        On Windows, signal handlers on sub-threads are silently skipped.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — signal handlers cannot be attached now.
            # They will be registered when the server/event-loop starts.
            logger.debug("attach_signal_handlers() called outside a running loop — skipping")
            return

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
            except (NotImplementedError, AttributeError):
                # Signal handlers not supported on Windows sub-threads
                pass

    async def wait_until_shutdown(self) -> None:
        """Block until shutdown signal is received."""
        await self._get_shutdown_event().wait()
