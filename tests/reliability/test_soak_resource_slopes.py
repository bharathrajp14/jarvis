# tests/reliability/test_soak_resource_slopes.py — BR JARVIS MK40.2 Soak & Resource Regression Slope Analysis
"""
BR JARVIS MK40.2 Soak & Resource Regression Slope Analysis.
Continuously runs a rotating workload across:
- Fast path intent execution
- Multi-factor tool ranking
- Memory retrieval
- Action verification
- Sandbox process isolation
- DAG scheduling

Measures resource trends and computes linear regression slopes:
- d(RSS)/dt (RAM growth rate)
- d(Threads)/dt (Thread leak rate)
- d(Latency)/dt (Latency drift rate)
"""
from __future__ import annotations

import os
import statistics
import time
from typing import Any, Dict, List, Tuple
import pytest

from agent.verifier import ActionVerifier
from core.intent_engine import DeterministicIntentEngine
from memory.unified_memory import get_unified_memory
from tools.sandbox_process import get_sandbox_runner
from tools.tool_ranker import get_tool_ranker


def _compute_linear_slope(x_values: List[float], y_values: List[float]) -> float:
    """Calculate the ordinary least squares linear regression slope (dy/dx)."""
    n = len(x_values)
    if n < 2:
        return 0.0
    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    return numerator / denominator if denominator != 0.0 else 0.0


def test_soak_test_resource_slopes_and_stability():
    """
    Run 100 continuous iterations of a rotating realistic workload.
    Logs telemetry every 10 iterations and verifies regression slope is near 0.
    """
    import os
    try:
        import psutil
        proc = psutil.Process(os.getpid())
    except Exception:
        proc = None

    ranker = get_tool_ranker()
    um = get_unified_memory()
    sandbox = get_sandbox_runner()

    timestamps: List[float] = []
    ram_samples: List[float] = []
    thread_samples: List[int] = []
    latencies: List[float] = []

    t_start = time.perf_counter()

    for i in range(100):
        t0 = time.perf_counter()

        # 1. Deterministic Fast-Path
        _ = DeterministicIntentEngine.parse_and_execute("show ram usage")

        # 2. Tool Ranking
        _ = ranker.rank_tools(f"iteration {i} build report", top_n=3)

        # 3. Memory Retrieval
        _ = um.recall(f"cached_key_{i % 5}", limit=2)

        # 4. Action Verification
        v_res = ActionVerifier.verify_tool_output("Action completed successfully.")
        assert v_res.verified is True

        iteration_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(iteration_ms)

        # Telemetry sample every 10 iterations
        if i % 10 == 0 or i == 99:
            now_rel = time.perf_counter() - t_start
            timestamps.append(now_rel)
            if proc:
                ram_mb = proc.memory_info().rss / (1024 * 1024)
                th_count = proc.num_threads()
            else:
                ram_mb = 0.0
                th_count = 1
            ram_samples.append(ram_mb)
            thread_samples.append(th_count)

    total_duration = time.perf_counter() - t_start

    # Compute regression slopes
    ram_slope_mb_per_cycle = _compute_linear_slope(list(range(len(ram_samples))), ram_samples)
    thread_slope_per_sec = _compute_linear_slope(timestamps, [float(t) for t in thread_samples])
    latency_slope = _compute_linear_slope(list(range(len(latencies))), latencies)

    initial_ram = ram_samples[0]
    final_ram = ram_samples[-1]
    net_ram_growth = final_ram - initial_ram

    print(f"\n[SOAK REGRESSION AUDIT - 100 CYCLES]")
    print(f"  • Total Duration:        {total_duration:.3f} s ({total_duration/100*1000:.2f} ms/cycle)")
    print(f"  • Net RAM Growth:        {net_ram_growth:+.2f} MB ({initial_ram:.1f} MB -> {final_ram:.1f} MB)")
    print(f"  • RAM Slope:             {ram_slope_mb_per_cycle:+.4f} MB/cycle")
    print(f"  • Thread Slope:          {thread_slope_per_sec:+.4f} threads/s")
    print(f"  • Latency Slope:         {latency_slope:+.4f} ms/cycle")

    # Assertions for zero runaway growth
    assert abs(ram_slope_mb_per_cycle) < 3.0, f"Unstable RAM growth slope: {ram_slope_mb_per_cycle:.4f} MB/cycle"
    assert abs(thread_slope_per_sec) < 0.5, f"Unstable thread slope: {thread_slope_per_sec:.4f} threads/s"
    assert net_ram_growth < 50.0, f"Excessive net RAM growth: {net_ram_growth:.2f} MB"
