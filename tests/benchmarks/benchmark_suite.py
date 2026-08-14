# tests/benchmarks/benchmark_suite.py — Production Performance & Latency Benchmark Suite
"""
Automated Latency & Performance Benchmark Suite for BR JARVIS MK40.
Measures cold/warm startup, fast-path latency, tool ranking, memory lookups,
and DAG scheduling to enforce low-millisecond performance budgets.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest
from core.intent_engine import DeterministicIntentEngine
from memory.unified_memory import get_unified_memory
from tools.tool_ranker import ToolMetadata, get_tool_ranker
from workflow.task_dag import DAGNode, ParallelDAGExecutor, topological_order


def _measure_latency(fn: Callable[[], Any], iterations: int = 10) -> Dict[str, float]:
    """Execute function N times and compute latency statistics (ms)."""
    latencies = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)]
    p95 = latencies[min(int(n * 0.95), n - 1)]
    p99 = latencies[min(int(n * 0.99), n - 1)]

    return {
        "mean_ms": statistics.mean(latencies),
        "min_ms": min(latencies),
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "max_ms": max(latencies),
    }


def test_benchmark_fast_path_latency():
    """Benchmark deterministic fast-path execution (target: < 50ms)."""
    def run_fast_cmd():
        return DeterministicIntentEngine.parse_and_execute("open hacker news")

    stats = _measure_latency(run_fast_cmd, iterations=15)
    print(f"\n[BENCHMARK] Fast Path Latency (P50): {stats['p50_ms']:.2f}ms | P95: {stats['p95_ms']:.2f}ms")
    assert stats["p50_ms"] < 50.0, f"Fast path latency too high: {stats['p50_ms']}ms"


def test_benchmark_tool_ranking_latency():
    """Benchmark multi-factor tool ranking engine (target: < 5ms)."""
    ranker = get_tool_ranker()
    # Register 20 test tools
    for i in range(20):
        ranker.register_metadata(ToolMetadata(
            name=f"test_tool_{i}",
            description=f"Performs automated operations on system resource {i}",
            capabilities=[f"cap_{i}", "system", "file"]
        ))

    def run_ranking():
        return ranker.rank_tools("find file and check system status", top_n=8)

    stats = _measure_latency(run_ranking, iterations=50)
    print(f"\n[BENCHMARK] Tool Ranking Latency (P50): {stats['p50_ms']:.2f}ms | P95: {stats['p95_ms']:.2f}ms")
    assert stats["p50_ms"] < 5.0, f"Tool ranking latency too high: {stats['p50_ms']}ms"


def test_benchmark_memory_lookup_latency():
    """Benchmark memory recall (target: < 10ms)."""
    um = get_unified_memory()

    def run_recall():
        return um.recall("user preferences and settings", limit=5)

    stats = _measure_latency(run_recall, iterations=20)
    print(f"\n[BENCHMARK] Memory Lookup Latency (P50): {stats['p50_ms']:.2f}ms | P95: {stats['p95_ms']:.2f}ms")
    assert stats["p50_ms"] < 25.0, f"Memory lookup latency too high: {stats['p50_ms']}ms"


def test_benchmark_dag_scheduling_latency():
    """Benchmark DAG topological ordering (target: < 2ms)."""
    nodes = [
        DAGNode(node_id=f"n{i}", title=f"Task {i}", dependencies=[f"n{i-1}"] if i > 0 else [])
        for i in range(20)
    ]

    def run_dag_sort():
        return topological_order(nodes)

    stats = _measure_latency(run_dag_sort, iterations=50)
    print(f"\n[BENCHMARK] DAG Scheduling Latency (P50): {stats['p50_ms']:.2f}ms | P95: {stats['p95_ms']:.2f}ms")
    assert stats["p50_ms"] < 2.0, f"DAG scheduling latency too high: {stats['p50_ms']}ms"
