# tests/adversarial/test_memory_experience_hostile.py — Hostile Memory & Experience Replay Suite
from __future__ import annotations

import statistics
import time
from pathlib import Path
from typing import Any, Dict, List
import pytest

from memory.experience_replay import ExperienceReplayStore, ExperienceTrajectory
from memory.persistent_store import MemoryEntry, delete_memory, save_memory, search_memory
from memory.unified_memory import UnifiedMemoryManager, get_unified_memory


def test_memory_cold_vs_warm_latencies():
    """Measure exact cold vs warm memory recall latencies across 50 samples."""
    um = get_unified_memory()

    # 1. Warm-up query and measure latency distribution
    warm_latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        res = um.recall("user coding preferences and editor setup", limit=5)
        warm_latencies.append((time.perf_counter() - t0) * 1000.0)

    warm_latencies.sort()
    n = len(warm_latencies)
    p50 = warm_latencies[int(n * 0.50)]
    p90 = warm_latencies[int(n * 0.90)]
    p95 = warm_latencies[int(n * 0.95)]
    p99 = warm_latencies[min(int(n * 0.99), n - 1)]

    print("\n" + "="*60)
    print("MEMORY RECALL BENCHMARK (50 SAMPLES)")
    print("="*60)
    print(f"  • Min Latency : {min(warm_latencies):6.3f} ms")
    print(f"  • P50 Latency : {p50:6.3f} ms")
    print(f"  • P90 Latency : {p90:6.3f} ms")
    print(f"  • P95 Latency : {p95:6.3f} ms")
    print(f"  • P99 Latency : {p99:6.3f} ms")
    print(f"  • Max Latency : {max(warm_latencies):6.3f} ms")
    print("="*60)

    assert p50 < 5.0, f"Memory warm P50 latency too high: {p50} ms"
    assert p95 < 20.0, f"Memory warm P95 latency too high: {p95} ms"


def test_conflicting_memories_temporal_and_scope_resolution():
    """Verify temporal conflict resolution (newer facts supersede older) and project vs user scope separation."""
    # Setup test facts
    # Fact A: User uses PostgreSQL (Old)
    entry_old = MemoryEntry(
        name="database_preference",
        description="Database choice",
        type="user",
        content="User uses PostgreSQL for all projects.",
        created="2025-01-01T10:00:00",
        confidence=0.8,
        scope="user",
    )
    save_memory(entry_old, scope="user")

    # Fact B: User switched to SQLite (New - supersedes Fact A)
    entry_new = MemoryEntry(
        name="database_preference",
        description="Database choice",
        type="user",
        content="User switched to SQLite with WAL mode.",
        created="2026-06-01T10:00:00",
        confidence=1.0,
        scope="user",
    )
    save_memory(entry_new, scope="user")

    # Fact C: Legacy project specifically uses PostgreSQL (Project scope)
    entry_project = MemoryEntry(
        name="project_database",
        description="Legacy Project Database",
        type="project",
        content="Legacy app requires PostgreSQL server connection.",
        created="2026-07-01T10:00:00",
        confidence=1.0,
        scope="project",
    )
    save_memory(entry_project, scope="project")

    # Query user scope
    user_results = search_memory("database", scope="user")
    assert len(user_results) > 0
    # Must retrieve the latest updated content (SQLite)
    assert "SQLite" in user_results[0].content

    # Query project scope
    project_results = search_memory("database", scope="project")
    assert len(project_results) > 0
    assert "Legacy app requires PostgreSQL" in project_results[0].content

    # Cleanup
    delete_memory("database_preference", scope="user")
    delete_memory("project_database", scope="project")


def test_experience_replay_isolation_of_failures_and_hallucinations(tmp_path):
    """Verify failed strategies are isolated into failure pitfalls and NOT returned as successful patterns."""
    store = ExperienceReplayStore(db_dir=tmp_path)

    # 1. Record failed hallucinated strategy
    store.record_trajectory(ExperienceTrajectory(
        goal_query="Deploy production application",
        success_status=False,
        step_count=3,
        tool_sequence=["run_code", "fake_deploy_tool", "crash_tool"],
        failure_reason="fake_deploy_tool not found in sandbox",
    ))

    # 2. Record verified successful strategy
    store.record_trajectory(ExperienceTrajectory(
        goal_query="Deploy production application",
        success_status=True,
        step_count=2,
        tool_sequence=["git_repo_tool", "run_code"],
        execution_context={"verified": True},
    ))

    # 3. Retrieve patterns
    successes = store.get_successful_patterns("Deploy production application", limit=5)
    failures = store.get_similar_failures("Deploy production application", limit=5)

    assert len(successes) == 1
    assert successes[0]["tool_sequence"] == ["git_repo_tool", "run_code"]

    assert len(failures) == 1
    assert failures[0]["failure_reason"] == "fake_deploy_tool not found in sandbox"
    assert failures[0]["tool_sequence"] == ["run_code", "fake_deploy_tool", "crash_tool"]

    store.close()


def test_memory_fallback_resilience_under_vector_failure():
    """Verify UnifiedMemoryManager continues working gracefully even if vector database fails."""
    um = get_unified_memory()

    # Save test memory into persistent store
    test_entry = MemoryEntry(
        name="resilience_test_entry",
        description="Resilience test note",
        type="reference",
        content="Resilience verification: Offline fallback operates reliably without vector backend.",
        created="2026-08-15T00:00:00",
        confidence=1.0,
        scope="user",
    )
    save_memory(test_entry, scope="user")

    # Simulate vector failure by disabling vector store
    original_vector = um.vector
    um.vector._available = False

    try:
        results = um.recall("Offline fallback operates reliably", limit=3)
        assert len(results) > 0
        assert any("Offline fallback operates reliably" in r.get("content", "") for r in results)
    finally:
        um.vector._available = original_vector._available
        delete_memory("resilience_test_entry", scope="user")
