# context/token_manager.py — BR JARVIS Token & Context Manager
"""
Token Budget Manager & Sliding Window History Trimmer.
Monitors token usage, enforces context window caps (default 12,000 tokens),
and tracks real-time token savings from Antigravity optimizations.
"""
from __future__ import annotations

import threading
import time


class TokenBudgetManager:
    """Singleton tracker for token consumption and Antigravity savings telemetry.

    FIXED: _instance_lock is now a class-level attribute (not set on the instance
    inside __new__) to prevent a race condition where record_usage() could be
    called before _instance_lock is assigned on the newly-created instance.
    """

    _instance = None
    _lock = threading.Lock()
    # Class-level lock used by all instance method calls (safe before instance is returned)
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst.tokens_consumed = 0
                inst.tokens_saved = 0
                inst.bypassed_calls = 0
                inst.start_time = time.time()
                cls._instance = inst
            return cls._instance

    def record_usage(self, consumed: int, saved: int = 0, is_bypassed: bool = False) -> None:
        """Record token usage and savings for telemetry (thread-safe)."""
        with self.__class__._instance_lock:
            self.tokens_consumed += consumed
            self.tokens_saved += saved
            if is_bypassed:
                self.bypassed_calls += 1

    def get_telemetry(self) -> dict:
        """Return real-time token efficiency metrics."""
        with self.__class__._instance_lock:
            elapsed = max(1.0, time.time() - self.start_time)
            total_attempted = self.tokens_consumed + self.tokens_saved
            efficiency_pct = (
                round((self.tokens_saved / total_attempted * 100), 1)
                if total_attempted > 0 else 0.0
            )
            return {
                "consumed": self.tokens_consumed,
                "saved": self.tokens_saved,
                "efficiency_pct": efficiency_pct,
                "bypassed_calls": self.bypassed_calls,
                "uptime_sec": round(elapsed, 1),
            }

    def reset(self) -> None:
        """Reset telemetry counters (for testing)."""
        with self.__class__._instance_lock:
            self.tokens_consumed = 0
            self.tokens_saved = 0
            self.bypassed_calls = 0
            self.start_time = time.time()


class ContextTokenTrimmer:
    """Sliding Window Context Trimmer to prevent context bloat."""

    MAX_HISTORY_TOKENS = 12_000

    @classmethod
    def trim_history(cls, history: list[dict], max_tokens: int = 12_000) -> list[dict]:
        """Trim conversation history to stay within max_tokens while preserving recent turns.

        FIXED: Uses a greedy fill-from-tail algorithm that checks ALL messages
        rather than stopping at the first message that doesn't fit.
        Estimate: 1 token ≈ 4 chars.
        """
        if not history:
            return []

        char_limit = max_tokens * 4
        # Work from newest to oldest, greedily filling up to the budget
        selected: list[dict] = []
        accumulated_chars = 0

        for msg in reversed(history):
            content = str(msg.get("content", ""))
            msg_chars = len(content)
            if accumulated_chars + msg_chars <= char_limit:
                selected.append(msg)
                accumulated_chars += msg_chars
            # FIXED: Don't break — continue checking smaller earlier messages

        # Restore chronological order
        return list(reversed(selected))
