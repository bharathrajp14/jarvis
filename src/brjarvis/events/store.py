# events/store.py — Bounded Event Store & Audit Log Engine
from __future__ import annotations

import atexit
import fnmatch
import logging
import queue
import threading
from collections import deque
from pathlib import Path
from typing import Deque, List, Optional

from brjarvis.core.paths import paths

from .types import BaseEvent

logger = logging.getLogger("JARVIS.EventStore")

EVENTS_FILE = paths.LOG_ROOT / "events.jsonl"


class EventStore:
    """Thread-safe bounded event history with non-blocking rotating persistence."""

    def __init__(
        self,
        persist_to_disk: bool = True,
        *,
        event_path: Optional[Path] = None,
        max_events: int = 5_000,
        max_pending_writes: int = 2_000,
        max_file_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 3,
    ):
        self._events: Deque[BaseEvent] = deque(maxlen=max(1, max_events))
        self._events_lock = threading.RLock()
        self.persist_to_disk = persist_to_disk
        self.event_path = Path(event_path or EVENTS_FILE)
        self.max_file_bytes = max(1_024, max_file_bytes)
        self.backup_count = max(1, backup_count)
        self._pending: queue.Queue[Optional[str]] = queue.Queue(maxsize=max(1, max_pending_writes))
        self._dropped_writes = 0
        self._closed = False
        self._writer: Optional[threading.Thread] = None
        if persist_to_disk:
            self._writer = threading.Thread(
                target=self._writer_loop,
                daemon=True,
                name="JarvisEventWriter",
            )
            self._writer.start()
            atexit.register(self.close)

    @property
    def dropped_writes(self) -> int:
        return self._dropped_writes

    def append(self, event: BaseEvent) -> None:
        """Store an event in bounded memory and enqueue disk persistence."""
        with self._events_lock:
            self._events.append(event)
        if self.persist_to_disk and not self._closed:
            try:
                self._pending.put_nowait(event.model_dump_json())
            except queue.Full:
                self._dropped_writes += 1
                logger.error(
                    "Event persistence queue is full; dropped event %s (total dropped=%d)",
                    event.event_id,
                    self._dropped_writes,
                )

    def query(
        self,
        topic_pattern: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[BaseEvent]:
        """Query a snapshot of historical events matching the supplied filters."""
        with self._events_lock:
            snapshot = list(self._events)
        results: List[BaseEvent] = []
        for event in reversed(snapshot):
            if topic_pattern and not fnmatch.fnmatch(event.topic, topic_pattern):
                continue
            if correlation_id and event.correlation_id != correlation_id:
                continue
            results.append(event)
            if len(results) >= max(0, limit):
                break
        return list(reversed(results))

    def clear(self) -> None:
        """Clear the bounded in-memory event history."""
        with self._events_lock:
            self._events.clear()

    def flush(self) -> None:
        """Wait until all queued event records have been persisted."""
        if self.persist_to_disk and self._writer is not None:
            self._pending.join()

    def close(self, timeout: float = 2.0) -> None:
        """Flush and stop the writer without blocking shutdown indefinitely."""
        if self._closed:
            return
        self._closed = True
        if not self.persist_to_disk or self._writer is None:
            return
        try:
            self._pending.put(None, timeout=max(0.1, timeout))
        except queue.Full:
            logger.error("Unable to enqueue event-writer shutdown sentinel")
            return
        self._writer.join(timeout=max(0.0, timeout))
        if self._writer.is_alive():
            logger.warning("Event writer did not stop within %.1fs", timeout)

    def _writer_loop(self) -> None:
        while True:
            payload = self._pending.get()
            try:
                if payload is None:
                    return
                self._write_line(payload)
            except Exception as exc:
                logger.error("Failed to persist event to disk: %s", exc, exc_info=True)
            finally:
                self._pending.task_done()

    def _write_line(self, payload: str) -> None:
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        encoded_size = len(payload.encode("utf-8")) + 1
        if self.event_path.exists() and self.event_path.stat().st_size + encoded_size > self.max_file_bytes:
            self._rotate_files()
        with self.event_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.write("\n")

    def _rotate_files(self) -> None:
        oldest = self.event_path.with_name(f"{self.event_path.name}.{self.backup_count}")
        oldest.unlink(missing_ok=True)
        for index in range(self.backup_count - 1, 0, -1):
            source = self.event_path.with_name(f"{self.event_path.name}.{index}")
            if source.exists():
                source.replace(self.event_path.with_name(f"{self.event_path.name}.{index + 1}"))
        if self.event_path.exists():
            self.event_path.replace(self.event_path.with_name(f"{self.event_path.name}.1"))
