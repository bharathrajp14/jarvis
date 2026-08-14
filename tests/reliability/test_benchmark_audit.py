# tests/reliability/test_benchmark_audit.py — BR JARVIS MK40.2 Benchmark Integrity & Latency Audit
"""
BR JARVIS MK40.2 Benchmark Integrity & Latency Audit.
Explicitly separates and measures:
1. Microbenchmarks (Isolated pure algorithms)
2. Component Benchmarks (Subsystems: Memory, Tool Ranker, DAG Scheduler, Sandbox)
3. End-to-End Benchmarks (Full pipeline: Intent -> Routing -> Tool -> Verification -> Response)

Calculates: P50, P90, P95, P99, min, max, mean, and stddev across 20+ repetitions.
"""
from __future__ import annotations

import math
import statistics
import time
from typing import Any, Callable, Dict, List
import pytest

from agent.verifier import ActionVerifier
from core.intent_engine import DeterministicIntentEngine
from core.sanitizer import InputSanitizer
from memory.persistent_store import search_memory
from memory.unified_memory import get_unified_memory
from tools.registry import execute_tool
from tools.tool_ranker import ToolMetadata, get_tool_ranker
from workflow.task_dag import DAGNode, topological_order


def _calculate_distribution(latencies_ms: List[float]) -> Dict[str, float]:
    """Compute rigorous statistical distribution metrics."""
    s = sorted(latencies_ms)
    n = len(s)
    mean_val = statistics.mean(s)
    stddev_val = statistics.stdev(s) if n > 1 else 0.0

    return {
        "count": n,
        "min_ms": s[0],
        "p50_ms": s[int(n * 0.50)],
        "p90_ms": s[min(int(n * 0.90), n - 1)],
        "p95_ms": s[min(int(n * 0.95), n - 1)],
        "p99_ms": s[min(int(n * 0.99), n - 1)],
        "max_ms": s[-1],
        "mean_ms": mean_val,
        "stddev_ms": stddev_val,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. MICROBENCHMARKS (Pure in-memory algorithms, 0 I/O)
# ─────────────────────────────────────────────────────────────────────────────

def test_microbenchmark_dag_topological_sort():
    """
    Microbenchmark: DAG topological ordering algorithm.
    Setup Included: No (nodes pre-constructed).
    External Network: No.
    Mocks: None.
    """
    nodes = [
        DAGNode(node_id=f"n_{i}", title=f"Task {i}", dependencies=[f"n_{i-1}"] if i > 0 else [])
        for i in range(25)
    ]

    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        ordered = topological_order(nodes)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
        assert len(ordered) == 25

    dist = _calculate_distribution(latencies)
    print(f"\n[MICROBENCHMARK: DAG Sort] P50: {dist['p50_ms']:.4f}ms | P95: {dist['p95_ms']:.4f}ms | P99: {dist['p99_ms']:.4f}ms | Mean: {dist['mean_ms']:.4f}ms ± {dist['stddev_ms']:.4f}ms")
    assert dist["p50_ms"] < 0.5, f"DAG sort P50 too slow: {dist['p50_ms']}ms"


def test_microbenchmark_input_sanitizer_shell_validation():
    """
    Microbenchmark: Shell command safety token parsing and injection checking.
    Setup Included: No.
    External Network: No.
    Mocks: None.
    """
    sample_cmds = [
        "python script.py --arg1 value",
        "cat file.txt | grep error",
        "dir /s /b C:\\workspace",
        "rm -rf / --no-preserve-root",
        "echo safe operation",
    ]

    latencies = []
    for _ in range(100):
        for cmd in sample_cmds:
            t0 = time.perf_counter()
            _ = InputSanitizer.validate_shell_safety(cmd)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

    dist = _calculate_distribution(latencies)
    print(f"\n[MICROBENCHMARK: Shell Sanitizer] P50: {dist['p50_ms']:.4f}ms | P95: {dist['p95_ms']:.4f}ms | P99: {dist['p99_ms']:.4f}ms | Mean: {dist['mean_ms']:.4f}ms ± {dist['stddev_ms']:.4f}ms")
    assert dist["p50_ms"] < 0.1, f"Shell sanitizer P50 too slow: {dist['p50_ms']}ms"


# ─────────────────────────────────────────────────────────────────────────────
# 2. COMPONENT BENCHMARKS (Subsystems with localized I/O & SQLite)
# ─────────────────────────────────────────────────────────────────────────────

def test_component_benchmark_tool_ranking():
    """
    Component Benchmark: Multi-factor token matching, capability boost, and safety scoring.
    Setup Included: No (metadata pre-registered).
    External Network: No.
    Mocks: None.
    """
    ranker = get_tool_ranker()
    queries = [
        "Find largest files in my workspace directory",
        "Analyze this excel spreadsheet and plot financial summary",
        "Check git commit history and push to origin",
        "Scan local ports for open network services",
        "Extract text from PDF report and summarize findings",
    ]

    latencies = []
    for _ in range(20):
        for q in queries:
            t0 = time.perf_counter()
            ranked = ranker.rank_tools(q, top_n=5)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
            assert len(ranked) > 0

    dist = _calculate_distribution(latencies)
    print(f"\n[COMPONENT BENCHMARK: Tool Ranker] P50: {dist['p50_ms']:.4f}ms | P95: {dist['p95_ms']:.4f}ms | P99: {dist['p99_ms']:.4f}ms | Mean: {dist['mean_ms']:.4f}ms ± {dist['stddev_ms']:.4f}ms")
    assert dist["p50_ms"] < 15.0, f"Tool ranker P50 too slow: {dist['p50_ms']}ms"


def test_component_benchmark_warm_memory_retrieval():
    """
    Component Benchmark: Warm-cache memory search across working, SQLite persistent, and lessons stores.
    Setup Included: No (cached stores).
    External Network: No (Local SQLite & RAM).
    Mocks: None.
    """
    um = get_unified_memory()
    # Warm up queries
    _ = um.recall("user development preferences", limit=3)

    latencies = []
    for _ in range(30):
        t0 = time.perf_counter()
        results = um.recall("user development preferences", limit=3)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    dist = _calculate_distribution(latencies)
    print(f"\n[COMPONENT BENCHMARK: Warm Memory Recall] P50: {dist['p50_ms']:.4f}ms | P95: {dist['p95_ms']:.4f}ms | P99: {dist['p99_ms']:.4f}ms | Mean: {dist['mean_ms']:.4f}ms ± {dist['stddev_ms']:.4f}ms")
    assert dist["p50_ms"] < 5.0, f"Memory recall P50 too slow: {dist['p50_ms']}ms"


# ─────────────────────────────────────────────────────────────────────────────
# 3. END-TO-END BENCHMARKS (Full Request -> Intent -> OS Action -> Verifier)
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_benchmark_deterministic_fast_path():
    """
    End-to-End Benchmark: Deterministic Fast-Path
    Full Chain: User input normalization -> Intent recognition -> OS Ctypes Action -> Output Verification.
    Setup Included: Yes (Real OS action).
    External Network: No (0 Tokens, Local OS).
    Mocks: None.
    """
    queries = [
        "Show CPU usage.",
        "Show RAM usage.",
        "Mute volume.",
        "Lock screen.",
    ]

    latencies = []
    for _ in range(15):
        for q in queries:
            t0 = time.perf_counter()
            # 1. Intent parse & execute
            res = DeterministicIntentEngine.parse_and_execute(q)
            assert res is not None and res.get("executed") is True
            # 2. Action verification
            v_res = ActionVerifier.verify_tool_output(res.get("result", ""))
            assert v_res.verified is True
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

    dist = _calculate_distribution(latencies)
    print(f"\n[E2E BENCHMARK: Fast-Path Full Chain] P50: {dist['p50_ms']:.4f}ms | P95: {dist['p95_ms']:.4f}ms | P99: {dist['p99_ms']:.4f}ms | Mean: {dist['mean_ms']:.4f}ms ± {dist['stddev_ms']:.4f}ms")
    assert dist["p50_ms"] < 15.0, f"E2E Fast-path P50 too slow: {dist['p50_ms']}ms"
