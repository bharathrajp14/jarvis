# core/lifecycle.py — Async Service Lifecycle & Signal Management for JARVIS MK37
from __future__ import annotations

import asyncio
import enum
import logging
import signal
import sys
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
        self._shutdown_event = asyncio.Event()

    def add_startup_hook(self, hook: HookCallable) -> None:
        """Register an async startup task."""
        self._startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: HookCallable) -> None:
        """Register an async cleanup/shutdown task."""
        self._shutdown_hooks.append(hook)

    async def startup(self) -> None:
        """Executes all registered startup hooks in order."""
        if self.state != SystemState.UNINITIALIZED:
            return
        self.state = SystemState.STARTING
        logger.info("🚀 Initiating System Startup Sequence...")

        for hook in self._startup_hooks:
            try:
                await asyncio.wait_for(hook(), timeout=15.0)
            except Exception as e:
                logger.error(f"❌ Startup hook error: {e}", exc_info=True)

        self.state = SystemState.RUNNING
        logger.info("✅ System State: RUNNING")

    async def shutdown(self) -> None:
        """Executes all registered shutdown hooks in reverse order."""
        if self.state in (SystemState.STOPPING, SystemState.SHUTDOWN):
            return
        self.state = SystemState.STOPPING
        logger.info("🛑 Initiating Graceful System Shutdown...")

        for hook in reversed(self._shutdown_hooks):
            try:
                await asyncio.wait_for(hook(), timeout=10.0)
            except Exception as e:
                logger.error(f"⚠️ Shutdown hook error: {e}")

        self.state = SystemState.SHUTDOWN
        self._shutdown_event.set()
        logger.info("👋 System State: SHUTDOWN complete")

    def attach_signal_handlers(self) -> None:
        """Register SIGINT and SIGTERM OS signal handlers."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop_policy().get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self.shutdown())
                )
            except (NotImplementedError, AttributeError):
                # Signal handlers not supported in windows sub-threads
                pass

    async def wait_until_shutdown(self) -> None:
        """Block until shutdown signal is received."""
        await self._shutdown_event.wait()
