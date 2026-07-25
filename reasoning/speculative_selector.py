# reasoning/speculative_selector.py — Dynamic Model Speed-Quality Speculative Selector
"""
Speculative Model Speed-Quality Selector for JARVIS.
Evaluates query complexity, latency targets, and token budget to dynamically select
between fast local models (Ollama/CTranslate2) and deep reasoning cloud models (Gemini/Claude).
"""
from __future__ import annotations

from typing import Dict, Any, Tuple


class SpeculativeModelSelector:
    """Dynamic multi-objective model profile selector."""

    def select_profile(self, user_query: str, max_latency_ms: int = 1500) -> Tuple[str, str]:
        """
        Evaluate query complexity and return (profile_name, rationale) tuple.
        Profiles: 'fast_local', 'balanced', 'deep_reasoning'.
        """
        if not user_query:
            return "fast_local", "Empty query default"

        query_low = user_query.lower()
        word_count = len(user_query.split())

        # Deep reasoning indicators
        is_complex = any(k in query_low for k in [
            "refactor", "architect", "why", "explain", "debug", "compare",
            "implement", "build", "design", "security", "audit"
        ]) or word_count > 30

        if is_complex:
            return "deep_reasoning", "Query requires high reasoning capacity"
        elif max_latency_ms <= 1000 or word_count <= 5:
            return "fast_local", "Short low-latency query suited for local fast execution"
        else:
            return "balanced", "Standard interactive query"
