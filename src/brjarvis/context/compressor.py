# context/compressor.py — Semantic Context Compressor & Noise Eliminator for JARVIS MK37
from __future__ import annotations

from .token_counter import TokenCounter

# Consistent chars-per-token ratio used throughout the context system
_CHARS_PER_TOKEN = 4


class ContextCompressor:
    """Compresses context strings to reduce token cost while preserving semantic meaning.

    Strategy: keep the first HEAD_RATIO of lines (setup/background) and the
    last TAIL_RATIO of lines (most recent/relevant). Tail is weighted more
    heavily because recent context is usually more important for task completion.
    """

    # 30% head (background context) + 70% tail (recent, most relevant)
    HEAD_RATIO: float = 0.30
    TAIL_RATIO: float = 0.70

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove redundant whitespace and empty lines."""
        if not text:
            return ""
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    @classmethod
    def compress(
        cls,
        text: str,
        max_tokens: int,
        *,
        head_ratio: float | None = None,
        tail_ratio: float | None = None,
    ) -> str:
        """Compress text to fit within the target token count.

        Args:
            text:       Input text to compress.
            max_tokens: Target maximum token count.
            head_ratio: Fraction of lines to keep from the head (default HEAD_RATIO).
            tail_ratio: Fraction of lines to keep from the tail (default TAIL_RATIO).

        Returns:
            Compressed text fitting within max_tokens.
        """
        head_ratio = head_ratio if head_ratio is not None else cls.HEAD_RATIO
        tail_ratio = tail_ratio if tail_ratio is not None else cls.TAIL_RATIO

        cleaned = cls.clean_text(text)
        current_tokens = TokenCounter.count(cleaned)

        if current_tokens <= max_tokens:
            return cleaned

        lines = cleaned.splitlines()

        if len(lines) <= 4:
            # Short text but long lines: truncate characters with consistent ratio
            max_chars = int(max_tokens * _CHARS_PER_TOKEN)
            return cleaned[:max_chars] + "\n... [truncated]"

        # Asymmetric head+tail split — tail gets more weight (most recent = most important)
        n_head = max(1, int(len(lines) * head_ratio))
        n_tail = max(1, int(len(lines) * tail_ratio))

        # Ensure we don't double-count lines
        if n_head + n_tail >= len(lines):
            n_tail = len(lines) - n_head

        head = lines[:n_head]
        tail = lines[-n_tail:] if n_tail > 0 else []
        omitted = len(lines) - n_head - n_tail

        summary_marker = f"\n... [{omitted} lines omitted for token optimization] ...\n"
        compressed_text = "\n".join(head) + summary_marker + "\n".join(tail)

        # Safety check: if still over budget, hard-truncate by chars
        if TokenCounter.count(compressed_text) > max_tokens:
            max_chars = int(max_tokens * _CHARS_PER_TOKEN)
            return compressed_text[:max_chars] + "..."

        return compressed_text
