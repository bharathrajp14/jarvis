# memory/domain.py — Canonical Memory Domain Entities, State Machine & Trust Model
"""
Authoritative Domain Entities and State Machine for BR JARVIS.
Defines the single canonical memory representation, lifecycle transitions,
source provenance hierarchy, and trust weighting.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("JARVIS.MemoryDomain")


# ── Secret Redaction Sentinel ──────────────────────────────────────────────────

def redact_secrets(text: str) -> str:
    """Scan and redact API keys, tokens, passwords, and secrets before persistence."""
    if not text or not isinstance(text, str):
        return text if text is not None else ""
    clean = text
    clean = re.sub(
        r"(?i)(api[_-]?key|token|secret|password|passwd|auth[_-]?key)\s*([:=]|\s+)\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?",
        r"\1\2 [REDACTED_SECRET]",
        clean,
    )
    clean = re.sub(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})", r"\1[REDACTED_SECRET]", clean)
    clean = re.sub(r"(?i)(ghp_[a-zA-Z0-9]{30,}|github_pat_[a-zA-Z0-9_]{40,})", r"[REDACTED_GITHUB_TOKEN]", clean)
    clean = re.sub(r"(?i)(xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,})", r"[REDACTED_SLACK_TOKEN]", clean)
    clean = re.sub(r"(?i)(AIzaSy[a-zA-Z0-9_\-]{33})", r"[REDACTED_GEMINI_KEY]", clean)
    clean = re.sub(r"(?i)(ntn_[a-zA-Z0-9_]{30,})", r"[REDACTED_NOTION_TOKEN]", clean)
    clean = re.sub(r"(?i)(sk-[a-zA-Z0-9\-_]{15,})", r"[REDACTED_API_KEY]", clean)
    return clean


# ── Memory Types ──────────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    """Explicit Memory Taxonomy for BR JARVIS."""
    WORKING = "WORKING"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    FACT = "FACT"
    PROCEDURAL = "PROCEDURAL"
    PREFERENCE = "PREFERENCE"
    CONSTRAINT = "CONSTRAINT"
    GOAL = "GOAL"
    DECISION = "DECISION"
    PROJECT_STATE = "PROJECT_STATE"
    USER_PROFILE = "USER_PROFILE"
    RELATIONSHIP = "RELATIONSHIP"
    LESSON = "LESSON"
    EXPERIENCE = "EXPERIENCE"
    OBSERVATION = "OBSERVATION"
    EVENT = "EVENT"
    REFERENCE = "REFERENCE"
    SYSTEM_KNOWLEDGE = "SYSTEM_KNOWLEDGE"

    @classmethod
    def from_str(cls, val: str) -> "MemoryType":
        try:
            return cls(val.upper())
        except (ValueError, AttributeError):
            mapping = {
                "user": cls.USER_PROFILE,
                "preference": cls.PREFERENCE,
                "feedback": cls.LESSON,
                "project": cls.PROJECT_STATE,
                "semantic": cls.SEMANTIC,
                "episodic": cls.EPISODIC,
                "operational": cls.PROCEDURAL,
                "reference": cls.REFERENCE,
                "notes": cls.SEMANTIC,
                "working": cls.WORKING,
                "decision": cls.DECISION,
                "constraint": cls.CONSTRAINT,
                "goal": cls.GOAL,
            }
            return mapping.get(str(val).lower(), cls.SEMANTIC)


# ── Memory Lifecycle State Machine ────────────────────────────────────────────

class MemoryStatus(str, Enum):
    """
    State machine for memory lifecycle:
      CANDIDATE -> VALIDATED -> ACTIVE -> (UPDATED | SUPERSEDED | INVALID | ARCHIVED | CONFLICTED)
    """
    CANDIDATE = "CANDIDATE"      # Newly extracted, pending validation/conflict resolution
    VALIDATED = "VALIDATED"      # Checked against rules and constraints
    ACTIVE = "ACTIVE"            # Authoritative current state
    UPDATED = "UPDATED"          # Modified with new version
    SUPERSEDED = "SUPERSEDED"    # Replaced by newer authoritative state; retained for history
    INVALID = "INVALID"          # Disproven or marked erroneous
    ARCHIVED = "ARCHIVED"        # Cold storage / compacted
    CONFLICTED = "CONFLICTED"    # Ambiguous collision requiring user resolution


# ── Provenance & Trust Hierarchy ──────────────────────────────────────────────

class SourceType(str, Enum):
    """Source authority hierarchy with associated reliability scores."""
    EXPLICIT_USER_CORRECTION = "explicit_user_correction"    # Reliability: 1.00
    EXPLICIT_USER_STATEMENT = "explicit_user_statement"      # Reliability: 0.95
    VERIFIED_TOOL_RESULT = "verified_tool_result"            # Reliability: 0.90
    VERIFIED_EXTERNAL_SOURCE = "verified_external_source"    # Reliability: 0.85
    SYSTEM_OBSERVATION = "system_observation"                # Reliability: 0.75
    STRONG_INFERENCE = "strong_inference"                    # Reliability: 0.60
    MODEL_INFERENCE = "model_inference"                      # Reliability: 0.40
    UNVERIFIED_ASSUMPTION = "unverified_assumption"          # Reliability: 0.20

    @property
    def default_reliability(self) -> float:
        weights = {
            SourceType.EXPLICIT_USER_CORRECTION: 1.00,
            SourceType.EXPLICIT_USER_STATEMENT: 0.95,
            SourceType.VERIFIED_TOOL_RESULT: 0.90,
            SourceType.VERIFIED_EXTERNAL_SOURCE: 0.85,
            SourceType.SYSTEM_OBSERVATION: 0.75,
            SourceType.STRONG_INFERENCE: 0.60,
            SourceType.MODEL_INFERENCE: 0.40,
            SourceType.UNVERIFIED_ASSUMPTION: 0.20,
        }
        return weights.get(self, 0.50)

    @classmethod
    def from_str(cls, val: str) -> "SourceType":
        try:
            return cls(val.lower())
        except (ValueError, AttributeError):
            mapping = {
                "user": cls.EXPLICIT_USER_STATEMENT,
                "user_correction": cls.EXPLICIT_USER_CORRECTION,
                "tool": cls.VERIFIED_TOOL_RESULT,
                "system": cls.SYSTEM_OBSERVATION,
                "model": cls.MODEL_INFERENCE,
                "inference": cls.STRONG_INFERENCE,
                "external": cls.VERIFIED_EXTERNAL_SOURCE,
                "consolidator": cls.SYSTEM_OBSERVATION,
            }
            return mapping.get(str(val).lower(), cls.MODEL_INFERENCE)


# ── Canonical Memory Entity ───────────────────────────────────────────────────

@dataclass
class CanonicalMemory:
    """
    The Single Canonical Memory Entity for BR JARVIS.
    All storage backends (SQLite, ChromaDB, caches) are subordinate to this schema.
    """
    memory_id: str = field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    user_id: str = "default_user"
    project_id: str = "global"
    scope: str = "user"                           # "user" | "project" | "session" | "task" | "system"
    namespace: str = "default"
    memory_type: MemoryType = MemoryType.SEMANTIC

    entity: str = ""                              # e.g., "python_version", "favorite_editor"
    attribute: str = ""                           # e.g., "primary_language", "theme"
    value: Any = ""                               # e.g., "Python 3.12", "dark_neon"
    content: str = ""                             # Human & model readable statement

    source_type: SourceType = SourceType.EXPLICIT_USER_STATEMENT
    source_id: str = ""                           # Identifier of message/tool/event
    evidence: str = ""                            # Ground-truth evidence or proof

    confidence: float = 1.0                       # 0.0 to 1.0
    reliability: float = 1.0                      # Derived from SourceType
    importance: float = 0.5                       # 0.0 to 1.0 (retrieval multiplier)

    created_at: float = field(default_factory=time.time)
    observed_at: float = field(default_factory=time.time)
    effective_from: float = field(default_factory=time.time)
    effective_until: Optional[float] = None       # None means currently active/open-ended
    updated_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    last_validated_at: float = field(default_factory=time.time)

    status: MemoryStatus = MemoryStatus.ACTIVE
    version: int = 1

    supersedes_memory_id: Optional[str] = None    # ID of previous memory this record replaces
    superseded_by_memory_id: Optional[str] = None  # ID of newer memory that replaced this record
    conflict_group_id: Optional[str] = None       # Group ID for clustered conflicting records

    session_id: str = ""
    task_id: str = ""
    decision_id: str = ""

    tags: List[str] = field(default_factory=list)
    content_hash: str = ""
    embedding_id: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.memory_type, str):
            self.memory_type = MemoryType.from_str(self.memory_type)
        if isinstance(self.status, str):
            try:
                self.status = MemoryStatus(self.status.upper())
            except ValueError:
                self.status = MemoryStatus.ACTIVE
        if isinstance(self.source_type, str):
            self.source_type = SourceType.from_str(self.source_type)

        if not self.reliability:
            self.reliability = self.source_type.default_reliability

        # Automatically format content if missing but entity/attribute/value are present
        if not self.content and (self.entity or self.attribute or self.value):
            parts = []
            if self.entity:
                parts.append(self.entity)
            if self.attribute:
                parts.append(f"({self.attribute})")
            if self.value:
                parts.append(f"= {self.value}")
            self.content = " ".join(parts)

        # Redact secrets before establishing hash
        self.content = redact_secrets(self.content)
        if isinstance(self.value, str):
            self.value = redact_secrets(self.value)

        if not self.content_hash:
            self.content_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute deterministic SHA-256 fingerprint for deduplication."""
        raw = f"{self.project_id}|{self.scope}|{self.entity}|{self.attribute}|{self.content}".strip().lower()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_currently_effective(self, at_time: Optional[float] = None) -> bool:
        """Check if memory is valid at a given timestamp (default: now)."""
        t = at_time if at_time is not None else time.time()
        if self.status != MemoryStatus.ACTIVE:
            return False
        if self.effective_from > t:
            return False
        if self.effective_until is not None and self.effective_until <= t:
            return False
        return True

    def mark_superseded(self, newer_memory_id: str, timestamp: Optional[float] = None) -> None:
        """Transition status to SUPERSEDED and record superseding chain."""
        t = timestamp if timestamp is not None else time.time()
        self.status = MemoryStatus.SUPERSEDED
        self.superseded_by_memory_id = newer_memory_id
        self.effective_until = t
        self.updated_at = t

    def to_dict(self) -> Dict[str, Any]:
        """Serialize canonical entity to dictionary."""
        d = asdict(self)
        d["memory_type"] = self.memory_type.value
        d["status"] = self.status.value
        d["source_type"] = self.source_type.value
        d["tags"] = list(self.tags)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanonicalMemory":
        """Deserialize canonical entity from dictionary."""
        d = dict(data)
        if "memory_type" in d:
            d["memory_type"] = MemoryType.from_str(d["memory_type"])
        if "status" in d:
            try:
                d["status"] = MemoryStatus(d["status"].upper())
            except Exception:
                d["status"] = MemoryStatus.ACTIVE
        if "source_type" in d:
            d["source_type"] = SourceType.from_str(d["source_type"])
        if "tags" in d and isinstance(d["tags"], str):
            try:
                d["tags"] = json.loads(d["tags"])
            except Exception:
                d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]

        # Filter unknown keys to prevent crashes
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)
