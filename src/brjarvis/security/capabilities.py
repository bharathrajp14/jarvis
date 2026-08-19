# security/capabilities.py — Canonical Capability Model & Tool Metadata
"""
Defines the authoritative capability-based security model for BR JARVIS.
Capabilities specify explicit operational permissions required by tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class Capability(str, Enum):
    """Explicit capability classes defining granular execution authorities."""
    READ_ONLY             = "read_only"
    USER_VISIBLE          = "user_visible"
    REVERSIBLE            = "reversible"
    EXTERNAL_SIDE_EFFECT  = "external_side_effect"
    DESTRUCTIVE           = "destructive"
    PRIVILEGED            = "privileged"
    CREDENTIAL_ACCESS     = "credential_access"
    NETWORK_ACCESS        = "network_access"
    COMMUNICATION         = "communication"
    FINANCIAL             = "financial"
    SYSTEM_CONTROL        = "system_control"
    CODE_EXECUTION        = "code_execution"
    BROWSER_CONTROL       = "browser_control"
    DESKTOP_CONTROL       = "desktop_control"
    FILE_MUTATION         = "file_mutation"


class RiskLevel(str, Enum):
    """Operational risk assessment levels."""
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class TrustLevel(str, Enum):
    """Provenance trust level for data flowing through the system."""
    TRUSTED_SYSTEM      = "trusted_system"
    VERIFIED_USER       = "verified_user"
    UNTRUSTED_EXTERNAL  = "untrusted_external"
    MODEL_PROPOSAL      = "model_proposal"


@dataclass(slots=True)
class ProvenanceMetadata:
    """Provenance metadata attached to all tool outputs and external inputs."""
    source: str
    trust_level: TrustLevel = TrustLevel.UNTRUSTED_EXTERNAL
    content_type: str = "text"
    timestamp: float = 0.0
    tool_name: str = ""
    sanitized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResultEnvelope:
    """Structured, provenance-aware envelope wrapping every tool execution output."""
    success: bool
    data: Any
    provenance: ProvenanceMetadata
    error: Optional[str] = None
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_s": self.duration_s,
            "provenance": {
                "source": self.provenance.source,
                "trust_level": self.provenance.trust_level.value,
                "content_type": self.provenance.content_type,
                "tool_name": self.provenance.tool_name,
                "timestamp": self.provenance.timestamp,
                "sanitized": self.provenance.sanitized,
            }
        }


class ToolContract(BaseModel):
    """Deterministic contract declared by every tool."""
    name: str
    version: str = "1.0.0"
    description: str
    capabilities: Set[Capability] = Field(default_factory=set)
    risk: RiskLevel = RiskLevel.LOW
    required_permissions: Set[str] = Field(default_factory=set)
    allowed_targets: List[str] = Field(default_factory=list)
    side_effects: bool = False
    reversible: bool = True
    cancellation_supported: bool = True
    timeout_s: float = 30.0
    requires_audit: bool = True
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = False
