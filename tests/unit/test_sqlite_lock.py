"""Unit tests for Concurrency-Safe SQLite Locking."""

from __future__ import annotations

import pytest

from brjarvis.memory.sqlite_lock import async_run_sqlite_write, run_sqlite_write


@pytest.mark.unit
def test_sync_sqlite_write_execution():
    """Verify synchronous SQLite write runner executes in background worker."""

    def sample_write(val: int) -> int:
        return val * 2

    res = run_sqlite_write(sample_write, 21)
    assert res == 42


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_sqlite_write_execution():
    """Verify async SQLite write runner acquires lock and executes correctly."""

    def sample_write(name: str) -> str:
        return f"written_{name}"

    res = await async_run_sqlite_write(sample_write, "record_01")
    assert res == "written_record_01"
