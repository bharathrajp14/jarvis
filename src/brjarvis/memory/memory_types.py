# memory/memory_types.py — Hierarchical Memory Taxonomy, Metadata & Execution Status
"""
Memory taxonomy, metadata schemas, and execution status constants for BR JARVIS MK40.2.
Distinguishes between Working, Episodic, Semantic, User Preference, Project, and Operational memory.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryTier(str, Enum):
    WORKING = "working"          # Active task/session scratchpad (ephemeral)
    EPISODIC = "episodic"        # Past events, session logs, audit outcomes
    SEMANTIC = "semantic"        # Reusable facts, environment, platform details
    PREFERENCE = "preference"    # User guidance, confirmation rules, styles
    PROJECT = "project"          # Project architecture, decisions, open tasks
    OPERATIONAL = "operational"  # Verified tool sequences, recovery lessons
    REFERENCE = "reference"      # Pointers to external systems, repositories, docs


class ConfidenceLevel(float, Enum):
    VERIFIED = 1.0               # Ground-truth verified against system/code/artifacts
    KNOWN_UNVERIFIED = 0.75      # Stated by user/model but not empirically verified
    INFERRED = 0.5               # Heuristically derived or synthesized
    OUTDATED = 0.2               # Marked stale due to newer contradictory facts
    UNKNOWN = 0.0                # Unconfirmed hypothesis


class ExecutionStatus(str, Enum):
    SUCCESS_VERIFIED = "SUCCESS_VERIFIED"      # Action executed and side-effect empirically verified
    SUCCESS_UNVERIFIED = "SUCCESS_UNVERIFIED"  # Action executed but side-effect not fully checked
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"        # Some steps succeeded, others failed
    FAILED = "FAILED"                          # Action threw error or failed verification
    TIMEOUT = "TIMEOUT"                        # Action exceeded execution time limit
    CANCELLED = "CANCELLED"                    # Action aborted by user or policy
    BLOCKED = "BLOCKED"                        # Security guardian or policy blocked execution


MEMORY_TYPES = [
    "user", "preference", "feedback", "project", "semantic", "episodic", "operational", "reference"
]

MEMORY_TYPE_DESCRIPTIONS: dict[str, str] = {
    "user": "Information about the user's role, goals, and communication preferences.",
    "preference": "User preferences regarding approvals, formatting, tool usage, and environments.",
    "feedback": "Guidance from past corrections: the rule, Why, and How to apply.",
    "project": "Project-scoped architecture, ongoing work, decisions, and milestones.",
    "semantic": "General durable facts about technologies, packages, and machine capabilities.",
    "episodic": "Historical events, past audits, session outcomes, and artifact references.",
    "operational": "Verified tool execution sequences, recovery actions, and failure lessons.",
    "reference": "Pointers to external repositories, docs, endpoints, trackers, and URLs.",
}

MEMORY_SYSTEM_PROMPT = """## Memory & Context
You have access to persistent memory across sessions.
Use remembered facts about the user, project architecture, ongoing tasks, and operational lessons to personalize responses and avoid repeated mistakes.
Maintain consistency with user preferences and ground-truth verified system facts."""



# ── Secret Redaction Sentinel ──────────────────────────────────────────────────


def redact_secrets(text: str) -> str:
    """Scan and redact API keys, tokens, passwords, and secrets before persistence."""
    if not text:
        return text
    clean = text
    # 1. Generic key=value or token=value or token sk-...
    clean = re.sub(r"(?i)(api[_-]?key|token|secret|password|passwd|auth[_-]?key)\s*([:=]|\s+)\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", r"\1\2 [REDACTED_SECRET]", clean)
    # 2. Bearer tokens
    clean = re.sub(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})", r"\1[REDACTED_SECRET]", clean)
    # 3. Known vendor token formats
    clean = re.sub(r"(?i)(ghp_[a-zA-Z0-9]{30,}|github_pat_[a-zA-Z0-9_]{40,})", r"[REDACTED_GITHUB_TOKEN]", clean)
    clean = re.sub(r"(?i)(xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,})", r"[REDACTED_SLACK_TOKEN]", clean)
    clean = re.sub(r"(?i)(AIzaSy[a-zA-Z0-9_\-]{33})", r"[REDACTED_GEMINI_KEY]", clean)
    clean = re.sub(r"(?i)(ntn_[a-zA-Z0-9_]{30,})", r"[REDACTED_NOTION_TOKEN]", clean)
    clean = re.sub(r"(?i)(sk-[a-zA-Z0-9\-_]{15,})", r"[REDACTED_API_KEY]", clean)
    return clean


# ── Full Memory Quality Schema ────────────────────────────────────────────────

@dataclass
class QualityMemoryRecord:
    """13-field Production Memory Quality Record with confidence and lifecycle metadata."""
    id: str
    type: str                                  # MemoryTier value or legacy type
    content: str
    source: str = "user"                       # "user" | "tool" | "system" | "document"
    timestamp: str = ""
    project_id: str = "global"                 # Scoping: "global" or specific project slug
    session_id: str = ""
    confidence: float = 1.0                    # 0.0 to 1.0 (ConfidenceLevel)
    importance: float = 0.5                    # 0.0 to 1.0
    recency: float = 1.0                       # 0.0 to 1.0 (decays over time)
    verified: bool = True
    expires_at: Optional[str] = None
    references: List[str] = field(default_factory=list)
    name: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name or self.id,
            "description": self.description,
            "type": self.type,
            "content": redact_secrets(self.content),
            "source": self.source,
            "timestamp": self.timestamp,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "confidence": self.confidence,
            "importance": self.importance,
            "recency": self.recency,
            "verified": self.verified,
            "expires_at": self.expires_at,
            "references": self.references,
        }
