# router.py — JARVIS MK37 Agent Router (Multi-Backend Intelligence)
"""
Intelligent routing with Gemini as the primary (and only required) backend.
Other backends are optional and load gracefully if keys are present.

Features:
- Smart task-based routing (code→GPT/Claude, private→Ollama, default→Gemini)
- Health-check-based fallback (skip unreachable backends)
- Runtime backend switching
"""
from __future__ import annotations

import os
import time
from enum import Enum


class AgentProfile(Enum):
    GEMINI   = "gemini"
    CLAUDE   = "claude"
    GPT      = "gpt"
    DEEPSEEK = "deepseek"
    OLLAMA   = "ollama"
    NVIDIA   = "nvidia"
    MISTRAL  = "mistral"


# Intelligent routing — route tasks to the best backend when available
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


def _get_configured_default() -> AgentProfile:
    try:
        from config.models import get_model_config
        cfg = get_model_config()
        default_str = cfg.get("default_backend", "gemini").lower()
        return _PROFILE_MAP.get(default_str, AgentProfile.GEMINI)
    except Exception:
        return AgentProfile.GEMINI


def load_available_backends() -> dict:
    """
    Attempt to initialize all backends.
    Gemini is REQUIRED. Others are optional and silently skipped.
    """
    backends = {}

    # ── Gemini (required) ────────────────────────────────────────────────
    try:
        from backends.gemini import GeminiBackend
        b = GeminiBackend()
        backends[AgentProfile.GEMINI] = b
        _print_ok(f"Gemini — {b.model_name}")
    except Exception as e:
        msg = f"  ✗ Gemini FAILED (required): {e}"
        print(msg)

    # ── Claude (optional) ────────────────────────────────────────────────
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from backends.anthropic import ClaudeBackend
            b = ClaudeBackend()
            if b.client:
                backends[AgentProfile.CLAUDE] = b
                _print_ok(f"Claude — {b.model_name}")
        except Exception as e:
            _print_skip(f"Claude: {e}")

    # ── OpenAI GPT (optional) ────────────────────────────────────────────
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from backends.openai_compat import OpenAIBackend
            b = OpenAIBackend()
            if b.client:
                backends[AgentProfile.GPT] = b
                _print_ok(f"GPT — {b.model_name}")
        except Exception as e:
            _print_skip(f"GPT: {e}")

    # ── DeepSeek (optional) ──────────────────────────────────────────────
    if os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENROUTER_API_KEY"):
        try:
            from backends.deepseek import DeepSeekBackend
            b = DeepSeekBackend()
            if b.client:
                backends[AgentProfile.DEEPSEEK] = b
                _print_ok(f"DeepSeek — {b.model_name}")
        except Exception as e:
            _print_skip(f"DeepSeek: {e}")

    # ── Ollama (optional — local) ────────────────────────────────────────
    try:
        from backends.ollama import OllamaBackend
        b = OllamaBackend()
        if b.ping(timeout=2.0):
            backends[AgentProfile.OLLAMA] = b
            _print_ok(f"Ollama — {b.model_name}")
    except Exception:
        pass  # Ollama not available — skip silently

    # ── Mistral (optional) ───────────────────────────────────────────────
    if os.environ.get("MISTRAL_API_KEY"):
        try:
            from backends.mistral import MistralBackend
            b = MistralBackend()
            if b.client:
                backends[AgentProfile.MISTRAL] = b
                _print_ok(f"Mistral — {b.model_name}")
        except Exception as e:
            _print_skip(f"Mistral: {e}")

    # ── NVIDIA NIM (optional) ────────────────────────────────────────────
    if os.environ.get("NVIDIA_API_KEY"):
        try:
            from backends.nvidia import NvidiaBackend
            b = NvidiaBackend()
            if b.client:
                backends[AgentProfile.NVIDIA] = b
                _print_ok(f"NVIDIA — {b.model_name}")
        except Exception as e:
            _print_skip(f"NVIDIA: {e}")

    return backends


def _has_rich():
    try:
        import rich
        return True
    except ImportError:
        return False


def _print_ok(msg: str):
    try:
        if _has_rich():
            from rich.console import Console
            Console().print(f"  [green]✓[/] {msg}")
        else:
            print(f"  ✓ {msg}")
    except Exception:
        print(f"  [OK] {msg}")


def _print_skip(msg: str):
    try:
        if _has_rich():
            from rich.console import Console
            Console().print(f"  [dim]⊘ {msg}[/]")
        else:
            print(f"  [SKIP] {msg}")
    except Exception:
        print(f"  [SKIP] {msg}")


class AgentRouter:
    """Routes tasks to the best available backend. Gemini is always the fallback."""

    def __init__(self, backends: dict | None = None):
        if backends is None:
            backends = load_available_backends()
        self.backends = backends
        self._health_cache: dict[AgentProfile, tuple[bool, float]] = {}
        self._health_ttl = 60.0  # Cache health checks for 60s
        self.tokens_consumed = {"input": 0, "output": 0, "total": 0}

        configured = _get_configured_default()
        if configured in backends:
            self.default = configured
        elif AgentProfile.GEMINI in backends:
            self.default = AgentProfile.GEMINI
        elif backends:
            self.default = list(backends.keys())[0]
        else:
            self.default = configured

    def _is_healthy(self, profile: AgentProfile) -> bool:
        """Check if a backend is healthy (with caching)."""
        if profile not in self.backends:
            return False
        cached = self._health_cache.get(profile)
        if cached and (time.monotonic() - cached[1]) < self._health_ttl:
            return cached[0]
        try:
            healthy = self.backends[profile].ping(timeout=3.0)
        except Exception:
            healthy = False
        self._health_cache[profile] = (healthy, time.monotonic())
        return healthy

    def route(self, task_keywords: list[str]) -> AgentProfile:
        """Find the best backend for given task keywords (with fallback chain)."""
        for kw in task_keywords:
            candidates = ROUTING_RULES.get(kw, [])
            for candidate in candidates:
                if candidate in self.backends:
                    return candidate
        return self.default

    def get_token_usage_stats(self) -> dict[str, int]:
        """Get the cumulative token statistics for all routing actions."""
        return self.tokens_consumed

    def run(self, profile: AgentProfile, messages: list, system: str = "") -> str:
        """Execute a completion on the given backend, with automatic fallback."""
        if profile not in self.backends:
            profile = self._find_fallback(profile)

        from context.token_counter import TokenCounter
        from events.bus import get_event_bus
        from events.types import BaseEvent

        input_tokens = TokenCounter.count(system) + TokenCounter.count(str(messages))
        self.tokens_consumed["input"] += input_tokens
        self.tokens_consumed["total"] += input_tokens

        backend = self.backends[profile]
        
        # Publish routing decision event
        try:
            get_event_bus().publish(BaseEvent(
                topic="model.route.selected",
                payload={
                    "backend": profile.value,
                    "model_name": backend.model_name,
                    "estimated_input_tokens": input_tokens
                }
            ))
        except Exception:
            pass

        try:
            res = backend.complete(messages, system)
            out_tokens = TokenCounter.count(res)
            self.tokens_consumed["output"] += out_tokens
            self.tokens_consumed["total"] += out_tokens
            return res
        except Exception as e:
            # Privacy Protection: If local_private requested Ollama, fail closed without cloud failover
            if profile == AgentProfile.OLLAMA:
                raise RuntimeError(
                    f"Privacy Protection Error: Local backend (Ollama) failed — {e}. "
                    "Task was marked 'local_private' and will NOT failover to cloud backends."
                ) from e
            # Try fallback on failure
            print(f"[Router] {profile.value} failed: {e} — trying fallback...")
            fallback = self._find_fallback(profile)
            if fallback != profile:
                res = self.backends[fallback].complete(messages, system)
                out_tokens = TokenCounter.count(res)
                self.tokens_consumed["output"] += out_tokens
                self.tokens_consumed["total"] += out_tokens
                return res
            raise

    def _find_fallback(self, exclude: AgentProfile = None) -> AgentProfile:
        """Find a working fallback backend."""
        if exclude == AgentProfile.OLLAMA:
            raise RuntimeError(
                "Privacy Protection Error: Local backend (Ollama) unavailable. "
                "Task was marked 'local_private' and will NOT failover to cloud backends."
            )
        # Priority: Gemini > GPT > Claude > DeepSeek > others
        priority = [AgentProfile.GEMINI, AgentProfile.GPT, AgentProfile.CLAUDE,
                     AgentProfile.DEEPSEEK, AgentProfile.OLLAMA, AgentProfile.MISTRAL, AgentProfile.NVIDIA]
        for p in priority:
            if p != exclude and p in self.backends:
                return p
        if self.backends:
            return list(self.backends.keys())[0]
        raise RuntimeError("No backends available")

    def switch_backend(self, backend_name: str) -> str:
        """Switch the default backend at runtime. Returns status message."""
        profile = _PROFILE_MAP.get(backend_name.lower())
        if profile is None:
            available = [p.value for p in self.backends.keys()]
            return f"Unknown backend '{backend_name}'. Available: {', '.join(available)}"
        if profile not in self.backends:
            available = [p.value for p in self.backends.keys()]
            return f"Backend '{backend_name}' is not loaded. Available: {', '.join(available)}"
        self.default = profile
        return f"Default backend switched to {profile.value} ({self.backends[profile].model_name})"

    def quick(self, prompt: str, system: str = "") -> str:
        """Quick single-turn completion via default backend."""
        backend = self.backends.get(self.default)
        if backend is None:
            raise RuntimeError("No default backend available")
        return backend.complete([{"role": "user", "content": prompt}], system)

    @property
    def gemini(self):
        """Direct access to Gemini backend."""
        return self.backends.get(AgentProfile.GEMINI)

    def select_multi_objective_backend(
        self,
        task_type: str = "general",
        w_quality: float = 1.0,
        w_cost: float = 0.5,
        w_latency: float = 0.5,
    ) -> AgentProfile:
        """
        Multi-objective optimization selecting backend balancing Quality, Cost, and Latency:
        Score = (Quality * w_quality) - (EstCost * w_cost) - (EstLatency * w_latency)
        """
        if not self.backends:
            raise RuntimeError("No backends available")

        # Performance & cost profiles (normalized 0.0 - 1.0)
        profile_metrics = {
            AgentProfile.GEMINI:   {"quality": 0.95, "cost": 0.1, "latency": 0.2},
            AgentProfile.GPT:      {"quality": 0.92, "cost": 0.4, "latency": 0.3},
            AgentProfile.CLAUDE:   {"quality": 0.98, "cost": 0.5, "latency": 0.4},
            AgentProfile.DEEPSEEK: {"quality": 0.96, "cost": 0.1, "latency": 0.5},
            AgentProfile.OLLAMA:   {"quality": 0.75, "cost": 0.0, "latency": 0.1},
            AgentProfile.MISTRAL:  {"quality": 0.85, "cost": 0.2, "latency": 0.2},
            AgentProfile.NVIDIA:   {"quality": 0.88, "cost": 0.3, "latency": 0.2},
        }

        best_profile = self.default
        best_score = -999.0

        for profile, backend in self.backends.items():
            metrics = profile_metrics.get(profile, {"quality": 0.8, "cost": 0.3, "latency": 0.3})
            score = (metrics["quality"] * w_quality) - (metrics["cost"] * w_cost) - (metrics["latency"] * w_latency)
            
            if score > best_score:
                best_score = score
                best_profile = profile

        return best_profile

    def get_status(self) -> dict:
        """Get status of all backends for display."""
        status = {}
        for profile, backend in self.backends.items():
            status[profile.value] = {
                "name": backend.name,
                "model": backend.model_name,
                "is_default": profile == self.default,
            }
        return status


_router_instance: AgentRouter | None = None

def get_router() -> AgentRouter:
    """Singleton getter for AgentRouter."""
    global _router_instance
    if _router_instance is None:
        _router_instance = AgentRouter()
    return _router_instance
