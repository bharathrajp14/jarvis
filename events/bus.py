# events/bus.py — Asynchronous Pub/Sub Event Bus for JARVIS MK37
from __future__ import annotations

import asyncio
import fnmatch
import inspect
import logging
import re
import threading
from collections import deque
from typing import Awaitable, Callable, Dict, Deque, List, Optional, Union, Any

from events.store import EventStore
from events.types import BaseEvent, ErrorEvent

logger = logging.getLogger("JARVIS.EventBus")

EventHandler = Callable[[BaseEvent], Union[None, Awaitable[None]]]

# Maximum DLQ entries — prevents unbounded memory growth
_DLQ_MAX = 1000


class EventBus:
    """High-performance async Pub/Sub Event Bus with wildcard topic routing and Dead Letter Queue."""

    def __init__(self, store: Optional[EventStore] = None):
        self.store: EventStore = store or EventStore()
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._sub_lock: threading.Lock = threading.Lock()
        # FIXED: Capped DLQ using deque with maxlen to prevent unbounded memory growth
        self._dlq: Deque[Dict[str, Any]] = deque(maxlen=_DLQ_MAX)
        # FIXED: Compiled regex cache to avoid re-compiling on every publish
        self._regex_cache: Dict[str, re.Pattern] = {}

    def subscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        """Subscribe a callback to a topic or wildcard pattern (e.g. 'system.*', 'task.#')."""
        with self._sub_lock:
            if topic_pattern not in self._subscribers:
                self._subscribers[topic_pattern] = []
            if handler not in self._subscribers[topic_pattern]:
                self._subscribers[topic_pattern].append(handler)
                logger.debug(f"EventBus: Registered subscriber for topic '{topic_pattern}'")

    def unsubscribe(self, topic_pattern: str, handler: EventHandler) -> bool:
        """Unsubscribe a callback handler. Returns True if removed."""
        with self._sub_lock:
            if topic_pattern in self._subscribers and handler in self._subscribers[topic_pattern]:
                self._subscribers[topic_pattern].remove(handler)
                return True
            return False

    def _match_topic(self, topic: str, pattern: str) -> bool:
        """Match topic against pattern using fnmatch or AMQP-style wildcard rules.

        FIXED: Compiled regex patterns are cached to avoid O(publish × compile) cost.
        """
        if topic == pattern or pattern == "*":
            return True
        if fnmatch.fnmatch(topic, pattern):
            return True
        # AMQP-style: '*' matches one segment, '#' matches any
        if pattern not in self._regex_cache:
            regex_str = (
                "^"
                + pattern.replace(".", r"\.").replace("*", r"[^.]+").replace("#", r".*")
                + "$"
            )
            self._regex_cache[pattern] = re.compile(regex_str)
        return bool(self._regex_cache[pattern].match(topic))

    def _collect_handlers(self, event: BaseEvent) -> List[EventHandler]:
        """Collect all matching handlers for an event topic (snapshot under lock)."""
        matching: List[EventHandler] = []
        with self._sub_lock:
            for pattern, handlers in self._subscribers.items():
                if self._match_topic(event.topic, pattern):
                    matching.extend(handlers)
        return matching

    def _push_dlq(self, event: BaseEvent, handler: EventHandler, error: str) -> None:
        """Push a failed handler record to the Dead Letter Queue (capped deque)."""
        self._dlq.append({
            "event":   event,
            "handler": getattr(handler, "__name__", str(handler)),
            "error":   error,
        })

    async def publish_async(self, event: BaseEvent) -> None:
        """Publish an event asynchronously to all matching subscriber callbacks."""
        self.store.append(event)
        logger.debug(f"📢 EventBus Publish: {event.topic} (ID: {event.event_id[:8]})")

        for handler in self._collect_handlers(event):
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error(
                    f"❌ EventBus handler error on topic '{event.topic}': {exc}",
                    exc_info=True,
                )
                self._push_dlq(event, handler, str(exc))

    def publish(self, event: BaseEvent) -> None:
        """Publish an event synchronously. Async handlers are scheduled on the running loop if available.

        FIXED: Async task errors are now captured via done-callback and added to DLQ.
        """
        self.store.append(event)
        logger.debug(f"📢 EventBus Publish: {event.topic} (ID: {event.event_id[:8]})")

        for handler in self._collect_handlers(event):
            try:
                if inspect.iscoroutinefunction(handler):
                    try:
                        loop = asyncio.get_running_loop()

                        def _make_done_cb(h: EventHandler, ev: BaseEvent):
                            def _done_cb(task: asyncio.Task):
                                exc = task.exception() if not task.cancelled() else None
                                if exc:
                                    logger.error(
                                        f"❌ EventBus async handler '{getattr(h, '__name__', h)}' "
                                        f"raised on topic '{ev.topic}': {exc}"
                                    )
                                    self._push_dlq(ev, h, str(exc))
                            return _done_cb

                        task = loop.create_task(handler(event))
                        task.add_done_callback(_make_done_cb(handler, event))

                    except RuntimeError:
                        # No running loop — skip async handler in sync context
                        logger.debug(
                            f"Skipping async handler '{getattr(handler, '__name__', '?')}' — no event loop"
                        )
                else:
                    handler(event)
            except Exception as exc:
                logger.error(
                    f"❌ EventBus handler error on topic '{event.topic}': {exc}",
                    exc_info=True,
                )
                self._push_dlq(event, handler, str(exc))

    def get_dlq(self) -> List[Dict[str, Any]]:
        """Retrieve dead-letter queue records (snapshot)."""
        return list(self._dlq)

    def clear_dlq(self) -> int:
        """Clear the DLQ and return the number of records removed."""
        count = len(self._dlq)
        self._dlq.clear()
        return count


# ── Global singleton ──────────────────────────────────────────────────────────
_global_event_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Return the global EventBus singleton (thread-safe)."""
    global _global_event_bus
    if _global_event_bus is not None:
        return _global_event_bus
    with _bus_lock:
        if _global_event_bus is None:
            _global_event_bus = EventBus()
    return _global_event_bus
