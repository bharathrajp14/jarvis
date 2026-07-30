# backends/base.py — JARVIS MK37 Abstract Backend Interface
"""
Abstract base class that ALL AI backends must implement.
Provides a consistent interface for completion, streaming, and health checks.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator, Any
import time


class BaseBackend(ABC):
    """Abstract base for all JARVIS MK37 AI backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name (e.g., 'Gemini', 'Claude')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Currently active model identifier."""
        ...

    @property
    def available(self) -> bool:
        """Return True if backend client is initialized and ready."""
        return getattr(self, "_client", None) is not None or getattr(self, "client", None) is not None

    @abstractmethod
    def complete(self, messages: list[dict], system: str = "", tools: list | None = None) -> str:
        """
        Synchronous chat completion.

        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": "..."} dicts.
            system: Optional system prompt (injected by orchestrator).
            tools: Optional tool definitions (backend-specific format).

        Returns:
            The assistant's text response.
        """
        ...

    @abstractmethod
    def stream(self, messages: list[dict], system: str = "") -> Generator[str, None, None]:
        """
        Streaming chat completion — yields text chunks as they arrive.

        Args:
            messages: Standard message list.
            system: Optional system prompt.

        Yields:
            Text chunks (strings).
        """
        ...

    def ping(self, timeout: float = 3.0) -> bool:
        """
        Quick health check — returns True if the backend is reachable.
        Default implementation tries a minimal completion.
        Override in subclasses for faster checks (e.g., HTTP /health endpoint).
        """
        try:
            start = time.monotonic()
            result = self.complete(
                [{"role": "user", "content": "ping"}],
                system="Reply with exactly: pong"
            )
            elapsed = time.monotonic() - start
            is_err = "error" in result.lower() or "failed" in result.lower()
            return bool(result) and not is_err and elapsed < timeout
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model_name!r}>"
