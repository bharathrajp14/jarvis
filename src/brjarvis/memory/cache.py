# memory/cache.py — High-Performance TTL Cache Engine for JARVIS MK37
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional
from core.native_bridge import fast_hash

logger = logging.getLogger("JARVIS.Cache")


class CacheEntry:
    def __init__(self, value: Any, ttl_seconds: float):
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class MemoryCache:
    """Thread-safe in-memory cache with FNV-1a key hashing and automatic TTL decay."""

    def __init__(self, default_ttl: float = 300.0):
        self.default_ttl = default_ttl
        self._store: Dict[int, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def _hash_key(self, key: str) -> int:
        """Hash key using fast native FNV-1a or fallback."""
        return fast_hash(key.encode("utf-8"))

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if present and not expired."""
        hk = self._hash_key(key)
        entry = self._store.get(hk)
        if entry is None:
            self.misses += 1
            return None

        if entry.is_expired:
            self._store.pop(hk, None)
            self.misses += 1
            return None

        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store value with specified or default TTL in seconds."""
        hk = self._hash_key(key)
        ttl_val = ttl if ttl is not None else self.default_ttl
        self._store[hk] = CacheEntry(value, ttl_val)

    def invalidate(self, key: str) -> bool:
        """Invalidate a cached key."""
        hk = self._hash_key(key)
        return self._store.pop(hk, None) is not None

    def clear(self) -> None:
        """Purge all cache entries."""
        self._store.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict[str, Any]:
        """Return cache performance statistics."""
        total = self.hits + self.misses
        hit_ratio = (self.hits / total * 100.0) if total > 0 else 0.0
        return {
            "entries_count": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio_percent": round(hit_ratio, 2),
        }
