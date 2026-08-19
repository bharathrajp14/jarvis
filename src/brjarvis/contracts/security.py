# src/brjarvis/contracts/security.py — Canonical Security & Guardian Contracts for BR JARVIS
"""
Canonical Security, Authorization, and Policy contracts for BR JARVIS operating runtime.
Defines ActionDecision, IdentityScope, PermissionContext, SecurityDecision, and SecretReference.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActionDecision(str, Enum):
    """Canonical Security Policy Decisions."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REDACT = "redact"
    ISOLATE = "isolate"

    # Compatibility aliases
    CONFIRM = "require_approval"


class IdentityScope(BaseModel):
    """Multi-dimensional caller identity and execution boundary."""
    user_id: str = "default_user"
    agent_id: str = "jarvis"
    device_id: str = "pc_primary"
    project_id: str = "global"
    workspace_id: str = "default"
    task_id: Optional[str] = None
    execution_id: Optional[str] = None
    environment: str = "host"  # host, browser, device, sandbox


class PermissionContext(BaseModel):
    """Contextual 6-tuple presented for deterministic security policy evaluation."""
    identity: IdentityScope = Field(default_factory=IdentityScope)
    resource: str = ""
    action: str = ""
    capability: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    previous_actions: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class SecurityDecision(BaseModel):
    """The authoritative verdict issued by Guardian and PolicyEngine."""
    decision: ActionDecision = ActionDecision.ALLOW
    reason: str = ""
    risk_level: str = "low"
    matched_policy: Optional[str] = None
    required_approvals: List[str] = Field(default_factory=list)
    redacted_fields: List[str] = Field(default_factory=list)
    isolated_environment: Optional[str] = None
    evaluated_at: float = Field(default_factory=time.time)

    def is_allowed(self) -> bool:
        return self.decision == ActionDecision.ALLOW


class SecretReference(BaseModel):
    """Reference pointer for credentials managed through SecretProvider (never raw keys in context)."""
    secret_id: str
    provider: str = "local"  # local, env, keyring, infisical
    key_name: str
    scope: str = "system"
    metadata: Dict[str, Any] = Field(default_factory=dict)
