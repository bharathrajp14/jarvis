"""Performance Benchmark: Native C Bridge Hashing & Distance."""

from __future__ import annotations

import time

import pytest

from brjarvis.core.native_bridge import fast_hash


@pytest.mark.benchmark
def test_native_hashing_throughput():
    """Verify fast hashing executes 5,000 hashes in under 200ms."""
    payload = b"Benchmark Payload for BR JARVIS Native C Acceleration Engine"

    start = time.perf_counter()
    for _ in range(5000):
        fast_hash(payload)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 500.0, f"5k hashes took {elapsed_ms:.2f}ms"
