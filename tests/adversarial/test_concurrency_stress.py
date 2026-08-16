# tests/adversarial/test_concurrency_stress.py — High-Concurrency Stress & Resource Leak Audit
from __future__ import annotations

import concurrent.futures
import os
import threading
import time
from typing import List
import pytest

from core.intent_engine import DeterministicIntentEngine
from memory.unified_memory import get_unified_memory
from tools.tool_ranker import ToolMetadata, get_tool_ranker
from workflow.task_dag import DAGNode, ParallelDAGExecutor, PersistentTaskDAG


def _get_process_ram_mb() -> float:
    """Return current process RAM consumption in MB."""
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        return proc.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


@pytest.mark.parametrize("concurrency_level", [10, 50, 100])
def test_high_concurrency_stress(tmp_path, concurrency_level):
    """Stress test system components at 10, 50, and 100 concurrent threads."""
    ranker = get_tool_ranker()
    um = get_unified_memory()
    # Warm-up to complete one-time C++ library allocation
    _ = ranker.rank_tools("warmup query", top_n=2)
    _ = um.recall("warmup recall", limit=1)

    import gc
    gc.collect()
    initial_ram = _get_process_ram_mb()
    initial_threads = threading.active_count()

    errors: List[Exception] = []
    error_lock = threading.Lock()

    def worker_task(idx: int):
        try:
            # 1. Deterministic Fast Path concurrent parse
            res = DeterministicIntentEngine.parse_and_execute(f"open app_{idx % 5}")

            # 2. Tool Ranker concurrent selection
            ranked = ranker.rank_tools(f"search files and inspect metrics for task {idx}", top_n=4)
            assert len(ranked) > 0

            # 3. Memory concurrent query
            mem_hits = um.recall(f"settings for user {idx % 10}", limit=3)
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            with error_lock:
                print(f"\n[WORKER {idx} EXCEPTION]\n{tb_str}")
                errors.append(e)

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_level) as pool:
        futures = [pool.submit(worker_task, i) for i in range(concurrency_level)]
        concurrent.futures.wait(futures)

    gc.collect()
    duration = time.perf_counter() - t0
    final_ram = _get_process_ram_mb()
    ram_delta = final_ram - initial_ram

    print(f"\n[STRESS TEST - {concurrency_level} WORKERS] Duration: {duration:.3f}s | RAM Delta: {ram_delta:+.2f}MB | Errors: {len(errors)}")

    assert len(errors) == 0, f"Concurrency errors occurred: {errors[:5]}"
    # Verify no runaway RAM leakage (growth < 60MB across up to 100 concurrent worker thread stacks)
    assert ram_delta < 60.0, f"Potential memory leak detected: {ram_delta:.2f}MB growth"
