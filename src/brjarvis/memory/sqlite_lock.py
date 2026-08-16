# memory/sqlite_lock.py — Centralized SQLite Writer Thread Pool for BR JARVIS MK38
from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Callable

logger = logging.getLogger("JARVIS.SQLiteLock")

import asyncio

# Centralized single-worker thread pool to serialize all SQLite write operations
_WRITE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="sqlite_writer")
_ASYNC_SQLITE_LOCK: asyncio.Lock | None = None


def _get_async_sqlite_lock() -> asyncio.Lock:
    global _ASYNC_SQLITE_LOCK
    if _ASYNC_SQLITE_LOCK is None:
        _ASYNC_SQLITE_LOCK = asyncio.Lock()
    return _ASYNC_SQLITE_LOCK


def run_sqlite_write(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Submits a write transaction to the single background writer thread.
    Blocks the caller synchronously until execution completes.
    """
    future = _WRITE_EXECUTOR.submit(func, *args, **kwargs)
    try:
        return future.result()
    except Exception as e:
        logger.exception("SQLite write execution failed in background thread")
        raise e


async def async_run_sqlite_write(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Asynchronously acquires the global SQLite lock and executes the write
    in the background worker thread with exponential backoff retries.
    """
    max_retries = 3
    delay = 0.05
    lock = _get_async_sqlite_lock()
    async with lock:
        for attempt in range(max_retries):
            try:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(_WRITE_EXECUTOR, lambda: func(*args, **kwargs))
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning("SQLite database is locked, retrying in %.2fs (attempt %d/%d)", delay, attempt + 1, max_retries)
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.exception("Async SQLite write failed after retries")
                    raise e
