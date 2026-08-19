# src/brjarvis/contracts/model.py — Canonical Model Runtime Contracts for BR JARVIS
"""
Canonical Model, Provider, and Routing contracts for BR JARVIS operating runtime.
Defines ModelCapability, ModelRequest, ModelResponse, ModelHealth, and ModelSelection.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelCapability(str, Enum):
    """Model feature and capability taxonomy."""

    TEXT = "text"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    REASONING = "reasoning"
    LONG_CONTEXT = "long_context"
    EMBEDDINGS = "embeddings"
    AUDIO = "audio"
    CODE = "code"


class ModelRequest(BaseModel):
    """Normalized completion request payload."""

    request_id: str = Field(default_factory=lambda: f"mreq-{uuid.uuid4().hex[:10]}")
    model_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    system_prompt: str = ""
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int = 4096
    stream: bool = False
    stop_sequences: List[str] = Field(default_factory=list)
    extra_headers: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class ModelResponse(BaseModel):
    """Normalized response envelope returned from model providers/gateways."""

    request_id: str = Field(default_factory=lambda: f"mresp-{uuid.uuid4().hex[:10]}")
    text: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    finish_reason: str = "stop"
    model: str = ""
    provider: str = "default"
    usage: Dict[str, int] = Field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )
    latency_ms: float = 0.0
    raw: Optional[Any] = None
    created_at: float = Field(default_factory=time.time)

    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class ModelHealth(BaseModel):
    """Live health and availability tracking for a model candidate."""

    model_id: str
    provider: str
    available: bool = True
    latency_p50_ms: float = 0.0
    error_rate: float = 0.0
    rate_limited: bool = False
    quota_exhausted: bool = False
    circuit_state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    last_success_at: Optional[float] = None
    last_failure_at: Optional[float] = None
    cost_per_m_in: float = 0.0
    cost_per_m_out: float = 0.0


class ModelSelection(BaseModel):
    """Explainable model routing decision record."""

    model_id: str
    provider: str
    score: float
    reason: str
    fallback_models: List[str] = Field(default_factory=list)
    task_type: str = "chat"
    complexity: str = "medium"
    selected_at: float = Field(default_factory=time.time)
