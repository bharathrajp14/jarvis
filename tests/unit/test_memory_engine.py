# tests/test_memory_engine.py — Unit Tests for Priority 4 Advanced Memory Engine
from __future__ import annotations

import time
import pytest
from memory.cache import MemoryCache
from memory.archiver import MemoryArchiver
from memory.unified_memory import UnifiedMemoryManager, get_unified_memory


def test_memory_cache_hit_and_expiry():
    cache = MemoryCache(default_ttl=0.1)  # 100ms TTL
    cache.set("test_key", {"status": "ok"})

    # Immediate hit
    res = cache.get("test_key")
    assert res == {"status": "ok"}
    assert cache.hits == 1

    # Wait for expiry
    time.sleep(0.15)
    res_expired = cache.get("test_key")
    assert res_expired is None
    assert cache.misses == 1


def test_memory_archiver_consolidation():
    archiver = MemoryArchiver()
    sample_history = [{"role": "user", "content": f"msg {i}"} for i in range(60)]

    retained = archiver.consolidate_history(sample_history, max_keep=40)
    assert len(retained) == 40
    assert retained[0]["content"] == "msg 20"


def test_unified_memory_manager():
    mem = get_unified_memory()
    mem.add_interaction("user", "Hello JARVIS")
    history = mem.get_conversation_history()

    assert len(history) > 0
    assert history[-1]["content"] == "Hello JARVIS"

    # Cache tool testing
    mem.cache_tool_result("search", {"query": "python"}, "Python is a programming language")
    cached = mem.get_cached_tool_result("search", {"query": "python"})
    assert cached == "Python is a programming language"
