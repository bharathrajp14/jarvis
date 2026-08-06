# events/handlers.py — Event Handler Decorators and Handler Registry for JARVIS MK37
from __future__ import annotations

from typing import Callable, Union
from events.bus import EventHandler, get_event_bus


def subscribe(topic_pattern: str):
    """Decorator to subscribe a function to an EventBus topic pattern.

    Usage:
        @subscribe("system.startup")
        async def on_startup(event: BaseEvent):
            if 'logger' in globals() or 'logger' in locals():
                logger.info("System booted!")
            else:
                import logging
                logging.getLogger(__name__).info("System booted!")
    """
    def decorator(fn: EventHandler):
        bus = get_event_bus()
        bus.subscribe(topic_pattern, fn)
        return fn
    return decorator
