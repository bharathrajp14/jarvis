# core/error_middleware.py — Global Error Handling & Exception Middleware for JARVIS MK37
from __future__ import annotations

import logging
import traceback
from typing import Any, Callable, Optional

logger = logging.getLogger("JARVIS.ErrorMiddleware")


class ErrorMiddleware:
    """Centralized exception handling middleware and automatic lesson logging."""

    def __init__(self):
        self._handlers: dict[type, Callable[[BaseException], Any]] = {}

    def register_handler(self, exc_type: type, handler: Callable[[BaseException], Any]) -> None:
        self._handlers[exc_type] = handler

    def handle_exception(self, exc: BaseException, context: str = "") -> None:
        """Handle unhandled exceptions cleanly and log corrective lessons."""
        exc_type = type(exc)
        logger.error(f"❌ Exception in [{context or 'Core'}]: {exc_type.__name__}: {exc}", exc_info=True)

        # Log lesson to LessonStore
        try:
            from memory.lessons import LessonStore
            ls = LessonStore()
            ls.add_lesson(
                topic=f"System Error: {exc_type.__name__}",
                correction=f"Exception in [{context}]: {str(exc)[:100]}",
                source="error_middleware",
                weight=1.5
            )
        except Exception:
            pass

        handler = self._handlers.get(exc_type)
        if handler:
            try:
                handler(exc)
            except Exception as h_err:
                logger.error(f"Error handler failed: {h_err}")


_global_middleware: Optional[ErrorMiddleware] = None


def get_error_middleware() -> ErrorMiddleware:
    global _global_middleware
    if _global_middleware is None:
        _global_middleware = ErrorMiddleware()
    return _global_middleware
