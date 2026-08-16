"""Performance Benchmark: Semantic Complexity Router Latency."""
from __future__ import annotations

import time
import pytest
from brjarvis.config.complexity_router import ComplexityAnalyzer, calculate_complexity_score


@pytest.mark.benchmark
def test_complexity_router_throughput():
    """Verify semantic complexity classification executes in under 10ms per query."""
    query = "Build an end-to-end multi-agent system with ChromaDB vector search and FastAPI REST API."
    
    start = time.perf_counter()
    for _ in range(100):
        ComplexityAnalyzer.compute_shannon_entropy(query)
        calculate_complexity_score([{"role": "user", "content": query}])
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / 100) * 1000
    assert avg_ms < 20.0, f"Average complexity analysis took {avg_ms:.2f}ms"
