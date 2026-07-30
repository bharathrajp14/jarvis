# router/core.py — JARVIS MK37 Agent Router (Multi-Backend Intelligence)
"""
Intelligent routing with Gemini as the primary (and only required) backend.
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
    """Attempt to initialize all backends. Gemini is REQUIRED. Others are optional."""
    backends = {}

    try:
        from backends import GeminiBackend
        g = GeminiBackend()
        if g.available:
            backends[AgentProfile.GEMINI] = g
    except Exception as e:
        print(f"[Router] Gemini init error: {e}")

    try:
        from backends import ClaudeBackend
        if ClaudeBackend:
            c = ClaudeBackend()
            if c.available:
                backends[AgentProfile.CLAUDE] = c
    except Exception:
        pass

    try:
        from backends import OpenAIBackend
        if OpenAIBackend:
            o = OpenAIBackend()
            if o.available:
                backends[AgentProfile.GPT] = o
    except Exception:
        pass

    try:
        from backends import DeepSeekBackend
        if DeepSeekBackend:
            d = DeepSeekBackend()
            if d.available:
                backends[AgentProfile.DEEPSEEK] = d
    except Exception:
        pass

    try:
        from backends import OllamaBackend
        if OllamaBackend:
            ol = OllamaBackend()
            if ol.available:
                backends[AgentProfile.OLLAMA] = ol
    except Exception:
        pass

    try:
        from backends import NvidiaBackend
        if NvidiaBackend:
            nv = NvidiaBackend()
            if nv.available:
                backends[AgentProfile.NVIDIA] = nv
    except Exception:
        pass

    try:
        from backends import MistralBackend
        if MistralBackend:
            m = MistralBackend()
            if m.available:
                backends[AgentProfile.MISTRAL] = m
    except Exception:
        pass

    return backends


class AgentRouter:
    """Intelligent multi-backend router with automatic fallback."""

    def __init__(self, backends: dict | None = None):
        self.backends = backends if backends is not None else load_available_backends()
        self.default  = _get_configured_default()
        self.fallback_history: list[dict] = []

        if AgentProfile.GEMINI not in self.backends:
            print("[Router] WARNING: Gemini backend not available. Check GEMINI_API_KEY in .env")

    def route(self, task_keywords: list[str]) -> AgentProfile:
        """Select best backend profile based on keywords."""
        for kw in task_keywords:
            candidates = ROUTING_RULES.get(kw, [])
            for c in candidates:
                if c in self.backends and self.backends[c].available:
                    return c

        if self.default in self.backends and self.backends[self.default].available:
            return self.default

        for profile, backend in self.backends.items():
            if backend.available:
                return profile

        return AgentProfile.GEMINI

    def run(self, profile: AgentProfile, messages: list[dict], system: str) -> str:
        """Run completion through selected profile with health-check fallback."""
        tried = []

        # Primary attempt
        backend = self.backends.get(profile)
        if backend and backend.available:
            try:
                res = backend.complete(messages, system)
                if res and not res.startswith("ERROR:"):
                    return res
            except Exception as e:
                tried.append((profile.value, str(e)))

        # Fallback order: Configured Default → Gemini → Any Available
        fallback_chain = [self.default, AgentProfile.GEMINI] + list(self.backends.keys())

        for f_profile in fallback_chain:
            if f_profile == profile or f_profile in [t[0] for t in tried]:
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
                        return res
                except Exception as e:
                    tried.append((f_profile.value, str(e)))

        return f"[BR: All backends failed. Attempted: {tried}]"


_router_instance: AgentRouter | None = None

def get_router() -> AgentRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = AgentRouter()
    return _router_instance
