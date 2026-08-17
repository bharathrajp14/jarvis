# router/core.py — JARVIS Multi-Backend Router with Strict Privacy Policy Enforcement
"""
Intelligent multi-backend router with privacy mode enforcement.
Prevents silent cloud fallback when local-only execution is requested.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.Router")


class PrivacyMode(str, Enum):
    LOCAL_ONLY      = "local_only"       # Strictly local models (Ollama). Zero cloud transmission.
    LOCAL_PREFERRED = "local_preferred"  # Prefer local; allow cloud fallback with warning.
    CLOUD_OPTIONAL  = "cloud_optional"   # Balance between local and cloud based on capabilities.
    CLOUD_REQUIRED  = "cloud_required"   # Cloud models only (Gemini, Claude, GPT, etc.).


class AgentProfile(Enum):
    GEMINI   = "gemini"
    CLAUDE   = "claude"
    GPT      = "gpt"
    DEEPSEEK = "deepseek"
    OLLAMA   = "ollama"
    NVIDIA   = "nvidia"
    MISTRAL  = "mistral"


ROUTING_RULES = {
    "code":           [AgentProfile.GEMINI, AgentProfile.CLAUDE, AgentProfile.GPT, AgentProfile.DEEPSEEK, AgentProfile.OLLAMA],
    "security":       [AgentProfile.GEMINI, AgentProfile.CLAUDE, AgentProfile.OLLAMA],
    "creative":       [AgentProfile.CLAUDE, AgentProfile.GEMINI, AgentProfile.GPT],
    "search":         [AgentProfile.GEMINI, AgentProfile.CLAUDE],
    "local_private":  [AgentProfile.OLLAMA],
    "long_context":   [AgentProfile.GEMINI, AgentProfile.CLAUDE],
    "gpu_inference":  [AgentProfile.NVIDIA, AgentProfile.GEMINI],
    "fast_inference": [AgentProfile.GEMINI, AgentProfile.MISTRAL, AgentProfile.OLLAMA],
    "multilingual":   [AgentProfile.GEMINI, AgentProfile.MISTRAL],
    "vision":         [AgentProfile.GEMINI, AgentProfile.CLAUDE],
    "analysis":       [AgentProfile.GEMINI, AgentProfile.CLAUDE, AgentProfile.GPT],
    "reasoning":      [AgentProfile.DEEPSEEK, AgentProfile.CLAUDE, AgentProfile.GEMINI],
}

_PROFILE_MAP = {p.value: p for p in AgentProfile}
_BACKENDS_CACHE: dict[AgentProfile, Any] | None = None
_BACKENDS_CACHE_TS = 0.0
_BACKENDS_CACHE_LOCK = threading.Lock()

try:
    from brjarvis.config.models import get_model_config
except Exception:
    def get_model_config() -> dict:  # type: ignore[misc]
        return {}

try:
    from brjarvis.integrations.backends import (
        GeminiBackend, OpenAIBackend, ClaudeBackend, DeepSeekBackend,
        OllamaBackend, NvidiaBackend, MistralBackend
    )
except Exception:
    GeminiBackend = None  # type: ignore[assignment, misc]
    OpenAIBackend = None  # type: ignore[assignment, misc]
    ClaudeBackend = None  # type: ignore[assignment, misc]
    DeepSeekBackend = None  # type: ignore[assignment, misc]
    OllamaBackend = None  # type: ignore[assignment, misc]
    NvidiaBackend = None  # type: ignore[assignment, misc]
    MistralBackend = None  # type: ignore[assignment, misc]


def _get_configured_default() -> AgentProfile:
    try:
        cfg = get_model_config()
        default_str = cfg.get("default_backend", "gemini").lower()
        return _PROFILE_MAP.get(default_str, AgentProfile.GEMINI)
    except Exception:
        return AgentProfile.GEMINI


def _get_configured_privacy_mode() -> PrivacyMode:
    mode_str = os.environ.get("JARVIS_PRIVACY_MODE", "cloud_optional").strip().lower()
    try:
        return PrivacyMode(mode_str)
    except Exception:
        return PrivacyMode.CLOUD_OPTIONAL


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def load_available_backends(*, force_refresh: bool = False) -> dict:
    """Attempt to initialize all backends safely."""
    global _BACKENDS_CACHE, _BACKENDS_CACHE_TS
    ttl_seconds = float(os.environ.get("JARVIS_BACKENDS_CACHE_TTL", "180"))

    if not force_refresh and _BACKENDS_CACHE is not None and (time.time() - _BACKENDS_CACHE_TS) < ttl_seconds:
        return dict(_BACKENDS_CACHE)

    with _BACKENDS_CACHE_LOCK:
        if not force_refresh and _BACKENDS_CACHE is not None and (time.time() - _BACKENDS_CACHE_TS) < ttl_seconds:
            return dict(_BACKENDS_CACHE)

        backends: dict[AgentProfile, Any] = {}

        try:
            if GeminiBackend is not None:
                g = GeminiBackend()
                if g.available:
                    backends[AgentProfile.GEMINI] = g
        except Exception as exc:
            logger.debug("[Router] Gemini init notice: %s", exc)

        try:
            if ClaudeBackend is not None and os.environ.get("ANTHROPIC_API_KEY", "").strip():
                c = ClaudeBackend()
                if c.available:
                    backends[AgentProfile.CLAUDE] = c
        except Exception:
            pass

        try:
            if OpenAIBackend is not None and os.environ.get("OPENAI_API_KEY", "").strip():
                o = OpenAIBackend()
                if o.available:
                    backends[AgentProfile.GPT] = o
        except Exception:
            pass

        try:
            has_deepseek = (
                os.environ.get("DEEPSEEK_API_KEY", "").strip()
                or os.environ.get("OPENROUTER_API_KEY", "").strip()
            )
            if DeepSeekBackend is not None and has_deepseek and not _truthy_env("JARVIS_DISABLE_DEEPSEEK"):
                d = DeepSeekBackend()
                if d.available:
                    backends[AgentProfile.DEEPSEEK] = d
        except Exception:
            pass

        try:
            if OllamaBackend is not None and not _truthy_env("JARVIS_DISABLE_OLLAMA"):
                ol = OllamaBackend()
                if ol.available:
                    backends[AgentProfile.OLLAMA] = ol
        except Exception:
            pass

        try:
            if NvidiaBackend is not None and os.environ.get("NVIDIA_API_KEY", "").strip():
                nv = NvidiaBackend()
                if nv.available:
                    backends[AgentProfile.NVIDIA] = nv
        except Exception:
            pass

        try:
            if MistralBackend is not None and os.environ.get("MISTRAL_API_KEY", "").strip():
                m = MistralBackend()
                if m.available:
                    backends[AgentProfile.MISTRAL] = m
        except Exception:
            pass

        _BACKENDS_CACHE = backends
        _BACKENDS_CACHE_TS = time.time()
        return dict(backends)


class AgentRouter:
    """Intelligent multi-backend router with strict privacy mode enforcement and automatic fallback."""

    def __init__(self, backends: dict | None = None, privacy_mode: Optional[PrivacyMode] = None):
        self.backends = backends if backends is not None else load_available_backends()
        self.default = _get_configured_default()
        self.privacy_mode = privacy_mode or _get_configured_privacy_mode()
        self.fallback_history: list[dict] = []

    def set_privacy_mode(self, mode: PrivacyMode) -> None:
        """Dynamically update privacy policy mode."""
        self.privacy_mode = mode
        logger.info("[Router] Active privacy mode set to %s", mode.value.upper())

    def route(self, task_keywords: list[str]) -> AgentProfile:
        """Select the best available backend profile based on task keywords and privacy policy."""
        # Enforce LOCAL_ONLY mode
        if self.privacy_mode == PrivacyMode.LOCAL_ONLY or "local_private" in task_keywords:
            if AgentProfile.OLLAMA in self.backends and self.backends[AgentProfile.OLLAMA].available:
                return AgentProfile.OLLAMA
            # Check any other local backend
            for prof, be in self.backends.items():
                if getattr(be, "is_local", False) and be.available:
                    return prof
            return AgentProfile.OLLAMA

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

        return self.default

    def run(
        self,
        profile: AgentProfile | str,
        messages: list[dict],
        system: str,
        task_id: str = "",
        goal: str = "",
    ) -> str:
        """Run completion through selected profile with privacy-aware fallback and structured diagnostics."""
        from brjarvis.router.diagnostics import (
            BackendAttempt,
            FailureType,
            TaskExecutionDiagnostic,
            classify_exception,
            TRANSIENT_FAILURE_TYPES,
            sanitize_diagnostic_text,
        )
        import uuid

        # Normalize profile if passed as a string
        if isinstance(profile, str):
            profile = _PROFILE_MAP.get(profile.lower(), AgentProfile.GEMINI)

        profile_val = profile.value if hasattr(profile, "value") else str(profile)

        trace_id = str(uuid.uuid4())[:8]
        effective_task_id = task_id or f"task_{trace_id}"
        effective_goal = goal or (messages[-1].get("content", "") if messages else "")

        diagnostic = TaskExecutionDiagnostic(
            trace_id=trace_id,
            task_id=effective_task_id,
            goal=str(effective_goal),
        )

        is_local_requested = (
            self.privacy_mode == PrivacyMode.LOCAL_ONLY or
            profile == AgentProfile.OLLAMA
        )

        # ── Primary backend attempt with bounded retry for transient errors ──
        backend = self.backends.get(profile)
        if backend and backend.available:
            max_retries = 2
            for attempt_idx in range(max_retries):
                t_start = time.monotonic()
                try:
                    res = backend.complete(messages, system)
                    latency = int((time.monotonic() - t_start) * 1000)
                    if res and not res.startswith("ERROR:"):
                        return res

                    # Backend returned error string
                    err_msg = res if res else "Empty response returned"
                    fail_type, clean_err = classify_exception(Exception(err_msg))
                    diagnostic.add_attempt(BackendAttempt(
                        provider=getattr(backend, "name", profile_val),
                        model=getattr(backend, "model_name", profile_val),
                        status="FAILED",
                        stage="provider_request",
                        error_type=fail_type,
                        error=clean_err,
                        latency_ms=latency,
                    ))

                    if fail_type not in TRANSIENT_FAILURE_TYPES or attempt_idx >= max_retries - 1:
                        break
                    time.sleep(1.0 * (2 ** attempt_idx))

                except Exception as exc:
                    latency = int((time.monotonic() - t_start) * 1000)
                    fail_type, clean_err = classify_exception(exc)
                    diagnostic.add_attempt(BackendAttempt(
                        provider=getattr(backend, "name", profile_val),
                        model=getattr(backend, "model_name", profile_val),
                        status="FAILED",
                        stage="provider_request",
                        error_type=fail_type,
                        error=clean_err,
                        latency_ms=latency,
                    ))
                    logger.warning("[Router] Primary backend '%s' attempt %d failed: %s", profile_val, attempt_idx + 1, clean_err)

                    if fail_type not in TRANSIENT_FAILURE_TYPES or attempt_idx >= max_retries - 1:
                        break
                    time.sleep(1.0 * (2 ** attempt_idx))
        else:
            diagnostic.add_attempt(BackendAttempt(
                provider=profile_val,
                model=getattr(backend, "model_name", profile_val) if backend else "unconfigured",
                status="FAILED",
                stage="model_routing",
                error_type=FailureType.MODEL_UNAVAILABLE,
                error=f"Backend profile '{profile_val}' is not configured or unavailable in active router.",
                latency_ms=0,
            ))

        # Strict Privacy Check: Do NOT fall back to cloud if local-only mode is active
        if self.privacy_mode == PrivacyMode.LOCAL_ONLY:
            diagnostic.final_reason = "LOCAL_ONLY_PRIVACY_BLOCKED"
            diagnostic.recovery_action = "Switch to cloud_optional privacy mode or ensure local Ollama daemon is running."
            logger.error("[Router] All local backends failed. Cloud fallback blocked by LOCAL_ONLY privacy mode.")
            return (
                f"TASK_EXECUTION_FAILED\n\n"
                f"{diagnostic.format_developer_trace()}\n\n"
                f"[BR JARVIS: Local backend(s) unavailable. Cloud fallback prohibited under active LOCAL_ONLY privacy policy. Final reason: all backends failed.]"
            )

        # Build deduplicated fallback chain
        raw_chain = [self.default, AgentProfile.GEMINI, AgentProfile.GPT] + list(self.backends.keys())
        fallback_chain = []
        for p in raw_chain:
            norm_p = _PROFILE_MAP.get(p.lower(), p) if isinstance(p, str) else p
            if norm_p not in fallback_chain:
                fallback_chain.append(norm_p)

        tried_profiles = {a.provider.lower() for a in diagnostic.attempts}

        for f_profile in fallback_chain:
            if f_profile == profile:
                continue
            f_profile_val = f_profile.value if hasattr(f_profile, "value") else str(f_profile)
            if f_profile_val.lower() in tried_profiles:
                continue

            f_backend = self.backends.get(f_profile)
            if f_backend and f_backend.available:
                if is_local_requested and not getattr(f_backend, "is_local", False):
                    continue

                t_start = time.monotonic()
                try:
                    res = f_backend.complete(messages, system)
                    latency = int((time.monotonic() - t_start) * 1000)
                    if res and not res.startswith("ERROR:"):
                        self.fallback_history.append({
                            "requested": profile_val,
                            "used": f_profile_val,
                            "time": time.time(),
                        })
                        logger.info("[Router] Fell back from '%s' to '%s' (Latency: %dms)", profile_val, f_profile_val, latency)
                        return res

                    err_msg = res if res else "Empty response returned"
                    fail_type, clean_err = classify_exception(Exception(err_msg))
                    diagnostic.add_attempt(BackendAttempt(
                        provider=getattr(f_backend, "name", f_profile_val),
                        model=getattr(f_backend, "model_name", f_profile_val),
                        status="FAILED",
                        stage="provider_request",
                        error_type=fail_type,
                        error=clean_err,
                        latency_ms=latency,
                    ))
                except Exception as exc:
                    latency = int((time.monotonic() - t_start) * 1000)
                    fail_type, clean_err = classify_exception(exc)
                    diagnostic.add_attempt(BackendAttempt(
                        provider=getattr(f_backend, "name", f_profile_val),
                        model=getattr(f_backend, "model_name", f_profile_val),
                        status="FAILED",
                        stage="provider_request",
                        error_type=fail_type,
                        error=clean_err,
                        latency_ms=latency,
                    ))

        # All backends failed — return full structured diagnostic output
        diagnostic.final_reason = "ALL_BACKENDS_FAILED"
        diagnostic.recovery_action = "Verify API keys in .env, check local gateway proxy (:8045), and ensure model quota is available."
        diagnostic.user_friendly_message = diagnostic.format_user_facing_summary()

        dev_trace = diagnostic.format_developer_trace()
        logger.error("[Router] Execution halted: %s\n%s", diagnostic.final_reason, dev_trace)

        return (
            f"TASK_EXECUTION_FAILED\n\n"
            f"{dev_trace}\n\n"
            f"[BR JARVIS: All backends failed. {diagnostic.user_friendly_message}]"
        )

    def get_status(self) -> dict[str, Any]:
        status = {}
        for profile, backend in self.backends.items():
            key = profile.value if hasattr(profile, "value") else str(profile)
            status[key] = {
                "name": getattr(backend, "name", key),
                "model": getattr(backend, "model_name", key),
                "available": getattr(backend, "available", False),
                "is_local": getattr(backend, "is_local", False),
                "is_default": (profile == self.default),
            }
        return {
            "privacy_mode": self.privacy_mode.value,
            "backends": status
        }

    def switch_backend(self, backend_name: str) -> str:
        name_lower = backend_name.lower().strip()
        for profile in self.backends.keys():
            key = profile.value if hasattr(profile, "value") else str(profile)
            if key.lower() == name_lower:
                backend = self.backends[profile]
                if not getattr(backend, "available", False):
                    return f"Backend '{key.upper()}' is registered but not currently available (check API keys / connectivity)."
                self.default = profile
                logger.info("[Router] Default backend switched to '%s'", key.upper())
                return f"Successfully switched default backend to {key.upper()}"

        available = [p.value if hasattr(p, "value") else str(p) for p in self.backends.keys()]
        return f"Unknown backend profile '{backend_name}'. Available: {available}"


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
