"""Adversarial Concurrency Stress Tests for SQLite Lock."""
from __future__ import annotations

import asyncio
import pytest
from brjarvis.memory.sqlite_lock import async_run_sqlite_write


@pytest.mark.adversarial
@pytest.mark.asyncio
async def test_high_concurrency_sqlite_contention():
    """Verify 30 concurrent async workers execute serialized writes through single worker thread without deadlock."""
    counter = 0

    def sync_increment(step: int) -> int:
        nonlocal counter
        current = counter
        counter = current + step
        return counter

    tasks = [async_run_sqlite_write(sync_increment, 1) for _ in range(30)]
    results = await asyncio.gather(*tasks)

    assert counter == 30
    assert len(results) == 30
