# events/store.py — Event Store & Audit Log Engine for JARVIS MK37
from __future__ import annotations

import fnmatch
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from .types import BaseEvent

logger = logging.getLogger("JARVIS.EventStore")

from brjarvis.core.paths import paths

EVENTS_FILE = paths.LOG_ROOT / "events.jsonl"


class EventStore:
    """In-memory and persistent Event Store for auditing and event replay."""

    def __init__(self, persist_to_disk: bool = True):
        self._events: List[BaseEvent] = []
        self.persist_to_disk = persist_to_disk

    def append(self, event: BaseEvent) -> None:
        """Store event in memory and optionally flush to events.jsonl."""
        self._events.append(event)
        if self.persist_to_disk:
            try:
                EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(EVENTS_FILE, "a", encoding="utf-8") as f:
                    f.write(event.model_dump_json() + "\n")
            except Exception as e:
                logger.error(f"Failed to persist event to disk: {e}")

    def query(
        self,
        topic_pattern: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[BaseEvent]:
        """Query historical events matching filters."""
        results: List[BaseEvent] = []
        for event in reversed(self._events):
            if topic_pattern and not fnmatch.fnmatch(event.topic, topic_pattern):
                continue
            if correlation_id and event.correlation_id != correlation_id:
                continue
            results.append(event)
            if len(results) >= limit:
                break
        return list(reversed(results))

    def clear(self) -> None:
        """Clear in-memory event store."""
        self._events.clear()
