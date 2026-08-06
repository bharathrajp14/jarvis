import pytest
import asyncio
from unittest.mock import MagicMock
from memory.sqlite_lock import async_run_sqlite_write

@pytest.mark.asyncio
async def test_concurrent_sqlite_writes():
    call_count = 0

    def mock_write(item_id: int):
        nonlocal call_count
        call_count += 1
        return f"written_{item_id}"

    tasks = [
        async_run_sqlite_write(mock_write, i)
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert call_count == 10
    assert results[0] == "written_0"
    assert results[9] == "written_9"
