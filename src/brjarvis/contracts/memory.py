# src/brjarvis/contracts/memory.py — Canonical Memory Contracts for BR JARVIS
"""
Canonical Memory and Knowledge contracts for BR JARVIS operating runtime.
Defines MemoryRecord, MemoryQuery, and MemoryFeedbackRecord.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from brjarvis.memory.domain import MemoryStatus, MemoryType, RetentionClass, SourceType


class MemoryRecord(BaseModel):
    """Canonical serializable Memory Entity contract."""

    memory_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    user_id: str = "default_user"
    project_id: str = "global"
    scope: str = "user"
    namespace: str = "default"
    memory_type: MemoryType = MemoryType.SEMANTIC
    entity: str = ""
    attribute: str = ""
    value: Any = ""
    content: str = ""
    source_type: SourceType = SourceType.EXPLICIT_USER_STATEMENT
    source_id: str = ""
    evidence: str = ""
    confidence: float = 1.0
    reliability: float = 1.0
    importance: float = 0.5
    created_at: float = Field(default_factory=time.time)
    observed_at: float = Field(default_factory=time.time)
    effective_from: float = Field(default_factory=time.time)
    effective_until: Optional[float] = None
    updated_at: float = Field(default_factory=time.time)
    last_accessed_at: float = Field(default_factory=time.time)
    last_validated_at: float = Field(default_factory=time.time)
    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1
    supersedes_memory_id: Optional[str] = None
    superseded_by_memory_id: Optional[str] = None
    conflict_group_id: Optional[str] = None
    session_id: str = ""
    task_id: str = ""
    decision_id: str = ""
    tags: List[str] = Field(default_factory=list)
    content_hash: str = ""
    embedding_id: Optional[str] = None
    retention_class: RetentionClass = RetentionClass.NORMAL


class MemoryQuery(BaseModel):
    """Specification for hybrid retrieval search over the memory plane."""

    query: str
    memory_type: Optional[MemoryType] = None
    scope: Optional[str] = None
    project_id: Optional[str] = None
    user_id: str = "default_user"
    limit: int = 10
    min_confidence: float = 0.0
    min_reliability: float = 0.0
    effective_at: Optional[float] = None


class MemoryFeedbackRecord(BaseModel):
    """Feedback signal recording retrieval relevance or accuracy."""

    feedback_id: str = Field(default_factory=lambda: f"mfb-{uuid.uuid4().hex[:8]}")
    memory_id: str
    session_id: str = ""
    query: str = ""
    signal: str = "HELPFUL"  # HELPFUL, UNHELPFUL, INCORRECT, OUTDATED
    note: str = ""
    created_at: float = Field(default_factory=time.time)
