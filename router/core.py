# router/core.py — JARVIS MK37 Agent Router (Multi-Backend Intelligence)
"""
Intelligent routing with Gemini as the primary (and only required) backend.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from enum import Enum
from typing import Any

logger = logging.getLogger("JARVIS.Router")


class AgentProfile(Enum):
    GEMINI   = "gemini"
    CLAUDE   = "claude"
    GPT      = "gpt"
    DEEPSEEK = "deepseek"
    OLLAMA   = "ollama"
    NVIDIA   = "nvidia"
    MISTRAL  = "mistral"


ROUTING_RULES = {
    "code":           [AgentProfile.GEMINI, AgentProfile.CLAUDE, AgentProfile.GPT, AgentProfile.DEEPSEEK],
    "security":       [AgentProfile.GEMINI, AgentProfile.CLAUDE],
    "creative":       [AgentProfile.CLAUDE, AgentProfile.GEMINI, AgentProfile.GPT],
    "search":         [AgentProfile.GEMINI, AgentProfile.CLAUDE],
    "local_private":  [AgentProfile.OLLAMA],
    "long_context":   [AgentProfile.GEMINI, AgentProfile.CLAUDE],
    "gpu_inference":  [AgentProfile.NVIDIA, AgentProfile.GEMINI],
    "fast_inference": [AgentProfile.GEMINI, AgentProfile.MISTRAL],
    "multilingual":   [AgentProfile.GEMINI, AgentProfile.MISTRAL],
    "vision":         [AgentProfile.GEMINI, AgentProfile.CLAUDE],
    "analysis":       [AgentProfile.GEMINI, AgentProfile.CLAUDE, AgentProfile.GPT],
    "reasoning":      [AgentProfile.DEEPSEEK, AgentProfile.CLAUDE, AgentProfile.GEMINI],
}

_PROFILE_MAP = {p.value: p for p in AgentProfile}
_BACKENDS_CACHE: dict[AgentProfile, Any] | None = None
_BACKENDS_CACHE_TS = 0.0
_BACKENDS_CACHE_LOCK = threading.Lock()


def _get_configured_default() -> AgentProfile:
    try:
        from config.models import get_model_config
        cfg = get_model_config()
        default_str = cfg.get("default_backend", "gemini").lower()
        return _PROFILE_MAP.get(default_str, AgentProfile.GEMINI)
    except Exception:
        return AgentProfile.GEMINI


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def load_available_backends(*, force_refresh: bool = False) -> dict:
    """Attempt to initialize all backends. Gemini is REQUIRED. Others are optional."""
    global _BACKENDS_CACHE, _BACKENDS_CACHE_TS
    ttl_seconds = float(os.environ.get("JARVIS_BACKENDS_CACHE_TTL", "180"))

    if not force_refresh and _BACKENDS_CACHE is not None and (time.time() - _BACKENDS_CACHE_TS) < ttl_seconds:
        return dict(_BACKENDS_CACHE)

    with _BACKENDS_CACHE_LOCK:
        if not force_refresh and _BACKENDS_CACHE is not None and (time.time() - _BACKENDS_CACHE_TS) < ttl_seconds:
            return dict(_BACKENDS_CACHE)

        backends: dict[AgentProfile, Any] = {}

        try:
            from backends import GeminiBackend
            g = GeminiBackend()
            if g.available:
                backends[AgentProfile.GEMINI] = g
        except Exception as exc:
            logger.warning(f"[Router] Gemini init error: {exc}")

        try:
            from backends import ClaudeBackend
            if ClaudeBackend and os.environ.get("ANTHROPIC_API_KEY", "").strip():
                c = ClaudeBackend()
                if c.available:
                    backends[AgentProfile.CLAUDE] = c
        except Exception:
            pass

        try:
            from backends import OpenAIBackend
            if OpenAIBackend and os.environ.get("OPENAI_API_KEY", "").strip():
                o = OpenAIBackend()
                if o.available:
                    backends[AgentProfile.GPT] = o
        except Exception:
            pass

        try:
            from backends import DeepSeekBackend
            has_deepseek = (
                os.environ.get("DEEPSEEK_API_KEY", "").strip()
                or os.environ.get("OPENROUTER_API_KEY", "").strip()
            )
            if DeepSeekBackend and has_deepseek and not _truthy_env("JARVIS_DISABLE_DEEPSEEK"):
                d = DeepSeekBackend()
                if d.available:
                    backends[AgentProfile.DEEPSEEK] = d
        except Exception:
            pass

        try:
            from backends import OllamaBackend
            if OllamaBackend and not _truthy_env("JARVIS_DISABLE_OLLAMA"):
                ol = OllamaBackend()
                if ol.available:
                    backends[AgentProfile.OLLAMA] = ol
        except Exception:
            pass

        try:
            from backends import NvidiaBackend
            if NvidiaBackend and os.environ.get("NVIDIA_API_KEY", "").strip():
                nv = NvidiaBackend()
                if nv.available:
                    backends[AgentProfile.NVIDIA] = nv
        except Exception:
            pass

        try:
            from backends import MistralBackend
            if MistralBackend and os.environ.get("MISTRAL_API_KEY", "").strip():
                m = MistralBackend()
                if m.available:
                    backends[AgentProfile.MISTRAL] = m
        except Exception:
            pass

        _BACKENDS_CACHE = backends
        _BACKENDS_CACHE_TS = time.time()
        return dict(backends)


class AgentRouter:
    """Intelligent multi-backend router with automatic fallback."""

    def __init__(self, backends: dict | None = None):
        self.backends = backends if backends is not None else load_available_backends()
        self.default = _get_configured_default()
        self.fallback_history: list[dict] = []

        if AgentProfile.GEMINI not in self.backends:
            logger.warning("[Router] Gemini backend not available. Check GEMINI_API_KEY in .env")

    def route(self, task_keywords: list[str]) -> AgentProfile:
        """Select the best available backend profile based on task keywords.

        FIXED: Now correctly verifies availability before returning a profile.
        Previously could return GEMINI even when it wasn't loaded.
        """
        for kw in task_keywords:
            candidates = ROUTING_RULES.get(kw, [])
            for candidate in candidates:
                if candidate in self.backends and self.backends[candidate].available:
                    return candidate

        # Fallback: configured default if available
        if self.default in self.backends and self.backends[self.default].available:
            return self.default

        # Last resort: first available backend
        for profile, backend in self.backends.items():
            if backend.available:
                return profile

        # No backend is available — return configured default and let run() handle the error
        logger.error("[Router] No available backend found. All backends offline.")
        return self.default

    def run(self, profile: AgentProfile, messages: list[dict], system: str) -> str:
        """Run completion through selected profile with health-check fallback.

        FIXED: Fallback chain is deduplicated to avoid retrying the same backend twice.
        """
        tried: list[tuple[str, str]] = []

        # Primary attempt
        backend = self.backends.get(profile)
        if backend and backend.available:
            try:
                res = backend.complete(messages, system)
                if res and not res.startswith("ERROR:"):
                    return res
            except Exception as exc:
                tried.append((profile.value, str(exc)))
                logger.warning(f"[Router] Primary backend '{profile.value}' failed: {exc}")

        # Build deduplicated fallback chain: Default → Gemini → remaining
        raw_chain = [self.default, AgentProfile.GEMINI] + list(self.backends.keys())
        # dict.fromkeys preserves order and deduplicates
        fallback_chain = list(dict.fromkeys(raw_chain))

        for f_profile in fallback_chain:
            # Skip the profile we already tried
            if f_profile == profile:
                continue
            # Skip profiles that already failed
            if f_profile.value in {t[0] for t in tried}:
                continue

            f_backend = self.backends.get(f_profile)
            if f_backend and f_backend.available:
                try:
                    res = f_backend.complete(messages, system)
                    if res and not res.startswith("ERROR:"):
                        self.fallback_history.append({
                            "requested": profile.value,
                            "used": f_profile.value,
                            "time": time.time(),
                        })
                        logger.info(
                            f"[Router] Fell back from '{profile.value}' to '{f_profile.value}'"
                        )
                        return res
                except Exception as exc:
                    tried.append((f_profile.value, str(exc)))

        return f"[BR: All backends failed. Attempted: {tried}]"

    def get_status(self) -> dict[str, Any]:
        """Return status dictionary of loaded model backends for API telemetry."""
        status = {}
        for profile, backend in self.backends.items():
            key = profile.value if hasattr(profile, "value") else str(profile)
            status[key] = {
                "name": getattr(backend, "name", key),
                "model": getattr(backend, "model_name", key),
                "available": getattr(backend, "available", False),
                "is_default": (profile == self.default),
            }
        return status

    def switch_backend(self, backend_name: str) -> str:
        """Switch active default backend profile.

        FIXED: Now validates that the backend is actually loaded and available.
        """
        name_lower = backend_name.lower().strip()
        for profile in self.backends.keys():
            key = profile.value if hasattr(profile, "value") else str(profile)
            if key.lower() == name_lower:
                backend = self.backends[profile]
                if not getattr(backend, "available", False):
                    return (
                        f"Backend '{key.upper()}' is registered but not currently available "
                        f"(check API keys / connectivity)."
                    )
                self.default = profile
                logger.info(f"[Router] Default backend switched to '{key.upper()}'")
                return f"Successfully switched default backend to {key.upper()}"

        available = [
            p.value if hasattr(p, "value") else str(p)
            for p in self.backends.keys()
        ]
        return f"Unknown backend profile '{backend_name}'. Available: {available}"


# ── Thread-safe singleton ─────────────────────────────────────────────────────
_router_instance: AgentRouter | None = None
_router_lock = threading.Lock()


def get_router() -> AgentRouter:
    """Return the global AgentRouter singleton (thread-safe)."""
    global _router_instance
    if _router_instance is not None:
        return _router_instance
    with _router_lock:
        if _router_instance is None:
            _router_instance = AgentRouter()
    return _router_instance
