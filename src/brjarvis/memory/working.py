# memory/working.py — JARVIS MK37 Working Memory (Thread-Safe)
from __future__ import annotations

import threading

_VALID_ROLES = {"user", "assistant", "system"}


class WorkingMemory:
    """Thread-safe sliding-window conversation history with root-goal pinning.

    Fixes over previous version:
    - All public methods are protected by a threading.Lock (prevents concurrent corruption)
    - add() validates the role parameter
    - pin_root() replaces external .history.insert(0, ...) calls
    - _char_count is properly maintained across all mutation paths
    """

    def __init__(self, max_tokens: int = 100_000):
        self.history: list[dict] = []
        self.max_tokens = max_tokens
        self._char_count = 0  # Running character count for O(1) trim checks
        self._lock = threading.Lock()

    @property
    def messages(self) -> list[dict]:
        """Alias for self.history — backwards compatibility."""
        return self.history

    def add(self, role: str, content: str) -> None:
        """Append a message to working memory.

        Args:
            role:    Must be 'user', 'assistant', or 'system'.
            content: Message text content.
        """
        if role not in _VALID_ROLES:
            role = "user"  # Safe default instead of crashing

        with self._lock:
            self.history.append({"role": role, "content": content})
            self._char_count += len(content)
            self._trim()

    def _trim(self) -> None:
        """Trim history to stay within token budget (must be called with lock held)."""
        if not self.history:
            return

        if self._char_count / 4 <= self.max_tokens:
            return

        # Pop non-root turns (index 1) first to satisfy token budget
        while len(self.history) > 1 and (self._char_count / 4) > self.max_tokens:
            removed = self.history.pop(1)
            self._char_count -= len(removed.get("content", ""))

        # If the single root message itself exceeds max_tokens, truncate its content
        if self.history and (len(self.history[0].get("content", "")) / 4) > self.max_tokens:
            max_chars = int(self.max_tokens * 4)
            old_len = len(self.history[0]["content"])
            self.history[0]["content"] = self.history[0]["content"][:max_chars]
            self._char_count -= old_len - max_chars

    def trim(self, max_turns: int = 10) -> None:
        """Trim working memory to max_turns while pinning the first (root goal) turn."""
        with self._lock:
            if len(self.history) <= max_turns:
                return
            root_msg = self.history[0]
            self.history = self.history[-max_turns:]
            # Re-pin root if it was dropped
            if not any(m is root_msg for m in self.history):
                self.history.insert(0, root_msg)
            # Recalculate char count after structural change
            self._char_count = sum(len(m.get("content", "")) for m in self.history)

    def pin_root(self, root_msg: dict) -> None:
        """Ensure root_msg is at index 0 (uses identity check, not equality).

        Replaces external .history.insert(0, root_msg) calls that bypass
        _char_count tracking.
        """
        with self._lock:
            if not any(m is root_msg for m in self.history):
                self.history.insert(0, root_msg)
                self._char_count += len(root_msg.get("content", ""))

    def get(self) -> list[dict]:
        """Return a snapshot of the current history (thread-safe copy)."""
        with self._lock:
            return list(self.history)

    def clear(self) -> None:
        """Clear all working memory history."""
        with self._lock:
            self.history.clear()
            self._char_count = 0

    def get_token_count(self) -> int:
        """Approximate token count (1 token ≈ 4 chars)."""
        with self._lock:
            return int(self._char_count / 4)

    def __len__(self) -> int:
        with self._lock:
            return len(self.history)
