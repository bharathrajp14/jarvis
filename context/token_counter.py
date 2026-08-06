# context/token_counter.py — Token Count Estimator & Accounting Engine for JARVIS MK37
from __future__ import annotations

import json
import logging
from typing import Any, Union

logger = logging.getLogger("JARVIS.TokenCounter")

try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
    _encoder = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_AVAILABLE = False
    _encoder = None


class TokenCounter:
    """Estimates and counts token consumption with tiktoken or fast char-ratio fallback."""

    @staticmethod
    def count(text: Union[str, list, dict, Any]) -> int:
        """Calculate token length for a string, message list, or dict representation."""
        if not text:
            return 0
        
        if isinstance(text, list):
            # Message list: sum content of turns
            total = 0
            for item in text:
                if isinstance(item, dict):
                    c = item.get("content", "")
                    total += TokenCounter.count(c) + 4  # ~4 overhead tokens per turn
                else:
                    total += TokenCounter.count(str(item))
            return max(1, total)

        if isinstance(text, dict):
            try:
                text = json.dumps(text, default=str)
            except Exception:
                text = str(text)
        elif not isinstance(text, str):
            text = str(text)

        if _TIKTOKEN_AVAILABLE and _encoder:
            try:
                return len(_encoder.encode(text))
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        # Fallback estimation: average 3.8 characters per token for English/Code
        return max(1, int(len(text) / 3.8))

    @staticmethod
    def is_tiktoken_enabled() -> bool:
        return _TIKTOKEN_AVAILABLE
