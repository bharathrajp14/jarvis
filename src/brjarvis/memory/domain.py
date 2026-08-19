# memory/domain.py — Canonical Memory Domain Entities, State Machine & Trust Model
"""
Authoritative Domain Entities and State Machine for BR JARVIS.
Defines the single canonical memory representation, lifecycle transitions,
source provenance hierarchy, and trust weighting.

This is the SINGLE canonical source for all memory types, enums, and entities.
All other modules must import from here — never define competing schemas.
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


# ── Secret Redaction Sentinel (CANONICAL — do NOT duplicate elsewhere) ─────────

def redact_secrets(text: str) -> str:
    """Scan and redact API keys, tokens, passwords, and secrets before persistence.

    This is the single canonical implementation. Do not duplicate or shadow it in
    other modules. All memory write paths must pass content through this function.
    """
    if not text or not isinstance(text, str):
        return text if text is not None else ""
    clean = text

    # 1. Generic key=value / token=value assignments
    clean = re.sub(
        r"(?i)(api[_-]?key|token|secret|password|passwd|auth[_-]?key|private[_-]?key)\s*([:=]|\s+)\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?",
        r"\1\2 [REDACTED_SECRET]",
        clean,
    )
    # 2. Bearer tokens in Authorization headers
    clean = re.sub(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})", r"\1[REDACTED_SECRET]", clean)
    # 3. GitHub tokens
    clean = re.sub(r"(?i)(ghp_[a-zA-Z0-9]{30,}|github_pat_[a-zA-Z0-9_]{40,})", r"[REDACTED_GITHUB_TOKEN]", clean)
    # 4. Slack tokens
    clean = re.sub(r"(?i)(xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,})", r"[REDACTED_SLACK_TOKEN]", clean)
    # 5. Google / Gemini API keys
    clean = re.sub(r"(?i)(AIzaSy[a-zA-Z0-9_\-]{33})", r"[REDACTED_GEMINI_KEY]", clean)
    # 6. Notion tokens
    clean = re.sub(r"(?i)(ntn_[a-zA-Z0-9_]{30,})", r"[REDACTED_NOTION_TOKEN]", clean)
    # 7. OpenAI / Anthropic / generic sk- keys
    clean = re.sub(r"(?i)(sk-[a-zA-Z0-9\-_]{15,})", r"[REDACTED_API_KEY]", clean)
    # 8. JWT tokens (three base64url segments separated by dots)
    clean = re.sub(
        r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",
        "[REDACTED_JWT]",
        clean,
    )
    # 9. SSH private key blocks
    clean = re.sub(
        r"-----BEGIN (RSA|EC|OPENSSH|DSA|ECDSA) PRIVATE KEY-----[\s\S]*?-----END \1 PRIVATE KEY-----",
        "[REDACTED_PRIVATE_KEY]",
        clean,
    )
    # 10. Database connection URLs with credentials
    clean = re.sub(
        r"(?i)(postgres|mysql|mongodb|redis|amqp)://[^:@\s]+:[^@\s]+@",
        r"\1://[REDACTED_CREDENTIALS]@",
        clean,
    )
    # 11. .env-style VARNAME=long_value assignments for sensitive keys
    clean = re.sub(
        r"(?im)^(\s*(?:DATABASE_URL|SECRET_KEY|PRIVATE_KEY|API_SECRET|AWS_SECRET|AZURE_KEY|GCP_KEY)\s*=\s*)(.+)$",
        r"\1[REDACTED_SECRET]",
        clean,
    )
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


# ── Retention Classes (controls decay behavior) ───────────────────────────────

class RetentionClass(str, Enum):
    """Durable retention policy for memory lifecycle and decay.

    Governs how long a memory survives without access before archival/expiry.
    The MemoryDecayEngine must respect these classes — PERMANENT memories are
    exempt from decay; EPHEMERAL memories expire within the same session.
    """
    EPHEMERAL = "EPHEMERAL"      # Session-scoped; expires at session end
    SHORT_TERM = "SHORT_TERM"    # Expires after ~1 day without access
    NORMAL = "NORMAL"            # Standard 7-day half-life (default)
    LONG_TERM = "LONG_TERM"      # 90-day half-life; survives infrequent access
    PERMANENT = "PERMANENT"      # Never decayed; immune to automated pruning

    @property
    def half_life_days(self) -> Optional[float]:
        """Return the half-life in days for decay calculation (None = exempt)."""
        mapping = {
            RetentionClass.EPHEMERAL: 0.0417,   # ~1 hour
            RetentionClass.SHORT_TERM: 1.0,
            RetentionClass.NORMAL: 7.0,
            RetentionClass.LONG_TERM: 90.0,
            RetentionClass.PERMANENT: None,      # Exempt from decay
        }
        return mapping.get(self, 7.0)

    @classmethod
    def for_memory_type(cls, memory_type: "MemoryType") -> "RetentionClass":
        """Return the default retention class for a given memory type."""
        type_map = {
            MemoryType.WORKING:         cls.EPHEMERAL,
            MemoryType.EPISODIC:        cls.NORMAL,
            MemoryType.SEMANTIC:        cls.LONG_TERM,
            MemoryType.FACT:            cls.LONG_TERM,
            MemoryType.PROCEDURAL:      cls.LONG_TERM,
            MemoryType.PREFERENCE:      cls.PERMANENT,
            MemoryType.CONSTRAINT:      cls.PERMANENT,
            MemoryType.GOAL:            cls.LONG_TERM,
            MemoryType.DECISION:        cls.LONG_TERM,
            MemoryType.PROJECT_STATE:   cls.LONG_TERM,
            MemoryType.USER_PROFILE:    cls.PERMANENT,
            MemoryType.RELATIONSHIP:    cls.LONG_TERM,
            MemoryType.LESSON:          cls.LONG_TERM,
            MemoryType.EXPERIENCE:      cls.NORMAL,
            MemoryType.OBSERVATION:     cls.SHORT_TERM,
            MemoryType.EVENT:           cls.SHORT_TERM,
            MemoryType.REFERENCE:       cls.NORMAL,
            MemoryType.SYSTEM_KNOWLEDGE: cls.LONG_TERM,
        }
        return type_map.get(memory_type, cls.NORMAL)


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
    retention_class: RetentionClass = RetentionClass.NORMAL  # Controls decay lifecycle

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
        if isinstance(self.retention_class, str):
            try:
                self.retention_class = RetentionClass(self.retention_class.upper())
            except ValueError:
                self.retention_class = RetentionClass.NORMAL

        if not self.reliability:
            self.reliability = self.source_type.default_reliability

        # Auto-assign retention class from memory type if still at default
        # (only override if it wasn't explicitly set by caller)
        if self.retention_class == RetentionClass.NORMAL:
            self.retention_class = RetentionClass.for_memory_type(self.memory_type)

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
        d["retention_class"] = self.retention_class.value
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
        if "retention_class" in d:
            try:
                d["retention_class"] = RetentionClass(d["retention_class"].upper())
            except Exception:
                d["retention_class"] = RetentionClass.NORMAL
        if "tags" in d and isinstance(d["tags"], str):
            try:
                d["tags"] = json.loads(d["tags"])
            except Exception:
                d["tags"] = [t.strip() for t in d["tags"].split(",") if t.strip()]

        # Filter unknown keys to prevent crashes
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


# ── Memory Feedback Signal ────────────────────────────────────────────────────

class FeedbackSignal(str, Enum):
    """Quality feedback signals for memory retrieval tuning."""
    HELPFUL = "helpful"          # Memory was correctly retrieved and useful
    NOT_HELPFUL = "not_helpful"  # Memory was retrieved but irrelevant
    STALE = "stale"              # Memory content is outdated
    WRONG = "wrong"              # Memory content is factually incorrect
    IRRELEVANT = "irrelevant"    # Memory matched query but did not help


@dataclass
class MemoryFeedback:
    """Structured feedback record for a specific memory retrieval event.

    Used to adjust retrieval quality scores over time.
    Persisted in the `memory_feedback` table in canonical DB.
    """
    feedback_id: str = field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:10]}")
    memory_id: str = ""              # The memory that was retrieved
    session_id: str = ""             # Session in which retrieval occurred
    query: str = ""                  # The query that triggered retrieval
    signal: FeedbackSignal = FeedbackSignal.HELPFUL
    note: str = ""                   # Optional free-text explanation
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "memory_id": self.memory_id,
            "session_id": self.session_id,
            "query": self.query,
            "signal": self.signal.value,
            "note": self.note,
            "created_at": self.created_at,
        }


# ── Handoff Object ────────────────────────────────────────────────────────────

class HandoffStatus(str, Enum):
    """Lifecycle states for a cross-session or cross-agent handoff."""
    OPEN = "OPEN"            # Created, not yet claimed by any agent
    CLAIMED = "CLAIMED"      # Claimed by a receiving agent
    DELIVERED = "DELIVERED"  # Successfully consumed and acknowledged
    EXPIRED = "EXPIRED"      # Passed expiry time without being claimed
    CANCELLED = "CANCELLED"  # Explicitly cancelled by source


@dataclass
class Handoff:
    """First-class handoff object for cross-session and cross-agent continuation.

    A Handoff is the structured record of everything a new session or agent needs
    to continue work without losing context. It is consumed once unless reusable=True.

    Persisted in the `handoffs` table in canonical DB.
    """
    handoff_id: str = field(default_factory=lambda: f"hnd_{uuid.uuid4().hex[:10]}")
    session_id: str = ""              # Source session that created this handoff
    project_id: str = "global"
    source_agent: str = "jarvis"      # Agent or model that created this
    target_agent: str = ""            # Intended recipient (empty = any)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None  # None = no expiry

    # Semantic content of the handoff
    goal: str = ""                    # The primary goal being handed off
    completed: List[str] = field(default_factory=list)  # What was finished
    current_state: str = ""           # Snapshot of where things stand
    failed_attempts: List[str] = field(default_factory=list)  # What was tried and failed
    decisions: List[str] = field(default_factory=list)  # Decisions made
    open_questions: List[str] = field(default_factory=list)  # Unresolved questions
    next_steps: List[str] = field(default_factory=list)  # Recommended actions
    important_files: List[str] = field(default_factory=list)  # Key files changed or relevant
    risks: List[str] = field(default_factory=list)  # Known risks or blockers
    confidence: float = 1.0          # Confidence in handoff completeness (0.0-1.0)

    status: HandoffStatus = HandoffStatus.OPEN
    reusable: bool = False            # If True, handoff is not consumed on first claim
    claimed_by: str = ""              # Agent that claimed this handoff
    claimed_at: Optional[float] = None
    delivered_at: Optional[float] = None

    def is_expired(self, at_time: Optional[float] = None) -> bool:
        """Check if the handoff has passed its expiry time."""
        t = at_time or time.time()
        return self.expires_at is not None and t > self.expires_at

    def claim(self, agent_id: str) -> bool:
        """Attempt to claim this handoff. Returns False if already claimed/consumed."""
        if self.status not in (HandoffStatus.OPEN,):
            return False
        if self.is_expired():
            self.status = HandoffStatus.EXPIRED
            return False
        self.status = HandoffStatus.CLAIMED
        self.claimed_by = agent_id
        self.claimed_at = time.time()
        return True

    def deliver(self) -> bool:
        """Mark handoff as delivered (consumed)."""
        if self.status not in (HandoffStatus.CLAIMED, HandoffStatus.OPEN):
            return False
        self.status = HandoffStatus.DELIVERED
        self.delivered_at = time.time()
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "session_id": self.session_id,
            "project_id": self.project_id,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "goal": self.goal,
            "completed": self.completed,
            "current_state": self.current_state,
            "failed_attempts": self.failed_attempts,
            "decisions": self.decisions,
            "open_questions": self.open_questions,
            "next_steps": self.next_steps,
            "important_files": self.important_files,
            "risks": self.risks,
            "confidence": self.confidence,
            "status": self.status.value,
            "reusable": self.reusable,
            "claimed_by": self.claimed_by,
            "claimed_at": self.claimed_at,
            "delivered_at": self.delivered_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Handoff":
        d = dict(data)
        if "status" in d:
            try:
                d["status"] = HandoffStatus(d["status"])
            except ValueError:
                d["status"] = HandoffStatus.OPEN
        for list_field in ("completed", "failed_attempts", "decisions",
                           "open_questions", "next_steps", "important_files", "risks"):
            if list_field in d and isinstance(d[list_field], str):
                try:
                    d[list_field] = json.loads(d[list_field])
                except Exception:
                    d[list_field] = []
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)
