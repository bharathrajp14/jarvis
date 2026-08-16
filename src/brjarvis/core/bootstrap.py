from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional

from .runtime import CoreRuntime, get_runtime
from brjarvis.events.bus import EventBus, get_event_bus
from brjarvis.events.types import SystemEvent
from brjarvis.orchestrator import JarvisOrchestrator
from brjarvis.router import AgentRouter, load_available_backends

logger = logging.getLogger(__name__)


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
            except Exception as e:
                logger.exception('Boot critical exception encountered in core/bootstrap.py')
                raise e
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


class CoreBootstrapper:
    """Unified System Bootstrapper Singleton for BR JARVIS."""

    _initialized: bool = False

    @classmethod
    def setup_environment(cls) -> dict:
        """Configure platform encoding, environment variables, and return status."""
        import json
        import platform
        import sys
        from pathlib import Path

        if cls._initialized:
            return cls.get_status()

        # Fix Windows terminal UTF-8 encoding
        if sys.platform == "win32":
            os.environ["PYTHONIOENCODING"] = "utf-8"
            try:
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                if hasattr(sys.stderr, "reconfigure"):
                    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        from brjarvis.core.paths import paths
        env_file = paths.DOTENV_FILE
        if env_file.exists():
            try:
                from dotenv import load_dotenv  # type: ignore[import-not-found]
                load_dotenv(env_file)
            except ImportError:
                pass

        cls._initialized = True
        return cls.get_status()

    @classmethod
    def get_status(cls) -> dict:
        """Get diagnostic status of system environment and keys."""
        import json
        import platform
        import sys
        from pathlib import Path
        from brjarvis.core.paths import paths

        config_path = paths.CONFIG_ROOT / "api_keys.json"
        api_keys = {
            "Gemini": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
            "Claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "GPT": bool(os.environ.get("OPENAI_API_KEY")),
            "Mistral": bool(os.environ.get("MISTRAL_API_KEY")),
            "NVIDIA": bool(os.environ.get("NVIDIA_API_KEY")),
        }

        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                if cfg.get("gemini_api_key"):
                    api_keys["Gemini"] = True
            except Exception:
                pass
        return {
            "initialized": cls._initialized,
            "platform": platform.system(),
            "python_version": sys.version.split()[0],
            "base_dir": str(paths.PROJECT_ROOT),
            "api_keys": api_keys,
        }

    @classmethod
    def initialize_runtime(cls, *, use_vector_memory: bool = True) -> AssistantRuntime:
        """Setup environment and build the AssistantRuntime singleton."""
        cls.setup_environment()
        return build_assistant_runtime(use_vector_memory=use_vector_memory)

