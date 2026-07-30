# events/bus.py — Asynchronous Pub/Sub Event Bus for JARVIS MK37
from __future__ import annotations

import asyncio
import fnmatch
import inspect
import logging
import re
import threading
from typing import Awaitable, Callable, Dict, List, Optional, Union, Any
from events.store import EventStore
from events.types import BaseEvent, ErrorEvent

logger = logging.getLogger("JARVIS.EventBus")

EventHandler = Callable[[BaseEvent], Union[None, Awaitable[None]]]


class EventBus:
    """High-performance async Pub/Sub Event Bus with wildcard topic routing and Dead Letter Queue."""

    def __init__(self, store: Optional[EventStore] = None):
        self.store: EventStore = store or EventStore()
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._sub_lock: threading.Lock = threading.Lock()
        self._dlq: List[Dict[str, Any]] = []

    def subscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        """Subscribe a callback to a topic or wildcard pattern (e.g. 'system.*', 'task.#')."""
        with self._sub_lock:
            if topic_pattern not in self._subscribers:
                self._subscribers[topic_pattern] = []
            if handler not in self._subscribers[topic_pattern]:
                self._subscribers[topic_pattern].append(handler)
                logger.debug(f"EventBus: Registered subscriber for topic pattern '{topic_pattern}'")

    def unsubscribe(self, topic_pattern: str, handler: EventHandler) -> bool:
        """Unsubscribe a callback handler."""
        with self._sub_lock:
            if topic_pattern in self._subscribers and handler in self._subscribers[topic_pattern]:
                self._subscribers[topic_pattern].remove(handler)
                return True
            return False

    def _match_topic(self, topic: str, pattern: str) -> bool:
        """Match topic against pattern using fnmatch or regex wildcard rules."""
        if topic == pattern or pattern == "*":
            return True
        if fnmatch.fnmatch(topic, pattern):
            return True
        regex = "^" + pattern.replace(".", r"\.").replace("*", r"[^.]+").replace("#", r".*") + "$"
        return bool(re.match(regex, topic))

    async def publish_async(self, event: BaseEvent) -> None:
        """Publish an event asynchronously to all matching subscriber callbacks."""
        self.store.append(event)
        logger.debug(f"📢 EventBus Publish: {event.topic} (ID: {event.event_id[:8]})")

        matching_handlers: List[EventHandler] = []
        with self._sub_lock:
            for pattern, handlers in self._subscribers.items():
                if self._match_topic(event.topic, pattern):
                    matching_handlers.extend(handlers)

        for handler in matching_handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"❌ EventBus handler error on topic '{event.topic}': {e}", exc_info=True)
                # Dead Letter Queue
                self._dlq.append({
                    "event": event,
                    "handler": getattr(handler, "__name__", str(handler)),
                    "error": str(e)
                })

    def publish(self, event: BaseEvent) -> None:
        """Publish an event synchronously. Fires async handlers via existing loop if available."""
        self.store.append(event)
        logger.debug(f"📢 EventBus Publish: {event.topic} (ID: {event.event_id[:8]})")

        matching_handlers: List[EventHandler] = []
        with self._sub_lock:
            for pattern, handlers in self._subscribers.items():
                if self._match_topic(event.topic, pattern):
                    matching_handlers.extend(handlers)

        for handler in matching_handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    # Try to schedule on an existing running loop
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        # No loop running — skip async handlers in sync context
                        logger.debug(f"Skipping async handler {getattr(handler, '__name__', '?')} — no event loop")
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"❌ EventBus handler error on topic '{event.topic}': {e}", exc_info=True)
                self._dlq.append({
                    "event": event,
                    "handler": getattr(handler, "__name__", str(handler)),
                    "error": str(e)
                })

    def get_dlq(self) -> List[Dict[str, Any]]:
        """Retrieve dead-letter queue records."""
        return list(self._dlq)


_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus
