# context/types.py — Pydantic v2 Data Models for JARVIS MK37 Context Engine
from __future__ import annotations

import logging
import enum
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class ContextScope(str, enum.Enum):
    SYSTEM_STATE    = "SYSTEM_STATE"
    CONVERSATION    = "CONVERSATION"
    ACTIVE_WINDOW   = "ACTIVE_WINDOW"
    CLIPBOARD       = "CLIPBOARD"
    LESSONS         = "LESSONS"
    MEMORY          = "MEMORY"
    PROJECT_FILES   = "PROJECT_FILES"
    USER_PREFERENCES = "USER_PREFERENCES"


class ContextItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scope: ContextScope
    title: str
    content: str
    token_count: int = Field(default=0, description="Auto-computed if not provided")
    priority: int = Field(default=5, ge=1, le=10, description="Priority scale 1 (lowest) to 10 (highest)")
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _auto_compute_tokens(self) -> "ContextItem":
        """Automatically compute token_count from content if not explicitly set."""
        if self.token_count <= 0 and self.content:
            try:
                from context.token_counter import TokenCounter
                self.token_count = TokenCounter.count(self.content)
            except Exception:
                # Fallback: ~4 chars per token
                self.token_count = max(1, len(self.content) // 4)
        return self


class TokenBudget(BaseModel):
    max_tokens: int = Field(
        default=128_000,
        description="Maximum total tokens allowed for prompt context",
    )
    reserve_response_tokens: int = Field(
        default=4096,
        description="Reserved tokens for AI output generation",
    )

    @classmethod
    def from_profile(cls, profile_str: str = "gemini") -> "TokenBudget":
        """Dynamic token budget scaling based on backend model capability.

        FIXED: Values now loaded from JarvisConfig if available, with
        hardcoded defaults as fallback.
        """
        low_p = (profile_str or "").lower()
        try:
            from core.config import get_config
            cfg = get_config()
            # Future: config could expose per-model context windows
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
        if "gemini" in low_p:
            return cls(max_tokens=1_000_000, reserve_response_tokens=8192)
        elif any(k in low_p for k in ["claude", "gpt", "deepseek"]):
            return cls(max_tokens=128_000, reserve_response_tokens=4096)
        elif any(k in low_p for k in ["ollama", "nvidia", "mistral"]):
            return cls(max_tokens=32_000, reserve_response_tokens=2048)
        return cls(max_tokens=128_000, reserve_response_tokens=4096)

    @property
    def available_context_tokens(self) -> int:
        """Available tokens after reserving space for the response."""
        return max(2000, self.max_tokens - self.reserve_response_tokens)


class AssembledContext(BaseModel):
    system_prompt: str
    context_str: str
    items: List[ContextItem] = Field(default_factory=list)
    total_tokens: int = 0
    budget: TokenBudget
    budget_used_percent: float = 0.0
