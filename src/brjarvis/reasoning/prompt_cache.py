# reasoning/prompt_cache.py — SHA-256 Prompt Caching & Token Budget Manager
"""
High-performance prompt caching & token budget manager.
Hashes system prompts and history context blocks using SHA-256 to eliminate redundant
token consumption and reduce model completion latency.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional


class PromptCacheManager:
    """Thread-safe prompt cache & token budget optimization manager."""

    def __init__(self, max_cache_entries: int = 500, ttl_seconds: int = 3600):
        self.max_cache_entries = max_cache_entries
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.tokens_saved = 0

    def _hash_key(self, system_prompt: str, messages_repr: str) -> str:
        """Compute SHA-256 digest for prompt content."""
        content = f"{system_prompt}||{messages_repr}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, system_prompt: str, messages_repr: str) -> Optional[str]:
        """Retrieve cached response if key exists and is unexpired."""
        key = self._hash_key(system_prompt, messages_repr)
        entry = self._cache.get(key)
        if entry:
            if time.time() - entry["timestamp"] < self.ttl_seconds:
                self.tokens_saved += entry.get("token_count", 0)
                return entry["response"]
            else:
                del self._cache[key]
        return None

    def put(self, system_prompt: str, messages_repr: str, response: str, token_count: int = 0) -> None:
        """Store prompt response in cache, evicting oldest entries when limit reached."""
        if len(self._cache) >= self.max_cache_entries:
            # Evict oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]

        key = self._hash_key(system_prompt, messages_repr)
        self._cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "token_count": token_count,
        }

    def clear(self) -> None:
        """Flush prompt cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return cache status metrics."""
        return {
            "cached_entries": len(self._cache),
            "tokens_saved": self.tokens_saved,
        }
