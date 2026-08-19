# src/brjarvis/contracts/tool.py — Canonical Tool & Capability Contracts for BR JARVIS
"""
Canonical Tool, Capability, and CapabilityLease contracts for BR JARVIS operating runtime.
Defines ToolRequest, ToolResult, Capability, CapabilityLease, and related Enums.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Functional categorization for tools and capabilities."""

    GENERAL = "general"
    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    DESKTOP = "desktop"
    DEVICE = "device"
    SHELL = "shell"
    SANDBOX = "sandbox"
    MEMORY = "memory"
    COMMUNICATION = "communication"
    DIAGNOSTICS = "diagnostics"
    CAREER = "career"
    SYSTEM = "system"


class RiskLevel(str, Enum):
    """Risk stratification for capabilities and actions."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolRequest(BaseModel):
    """Canonical invocation request for a tool or capability."""

    request_id: str = Field(default_factory=lambda: f"treq-{uuid.uuid4().hex[:10]}")
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_id: str = Field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}")
    trace_id: str = Field(default_factory=lambda: f"tr-{uuid.uuid4().hex[:16]}")
    task_id: str = ""
    session_id: str = ""
    agent_id: str = "jarvis"
    environment: str = "host"  # host, browser, device, sandbox
    lease_id: Optional[str] = None
    timeout_sec: float = 30.0
    confirmed: bool = False
    created_at: float = Field(default_factory=time.time)


class ToolResult(BaseModel):
    """Canonical result envelope returned by tool execution."""

    tool_name: str
    status: str = "COMPLETED"  # COMPLETED, FAILED, TIMEOUT, CANCELLED, BLOCKED
    success: bool = True
    data: Optional[Any] = None
    output: str = ""
    evidence: str = ""
    verified: bool = True
    error_code: Optional[str] = None
    message: str = ""
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_ms: float = 0.0
    side_effects: List[str] = Field(default_factory=list)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class Capability(BaseModel):
    """First-class registered capability definition."""

    id: str  # e.g., "filesystem.read", "browser.click", "shell.exec"
    version: str = "1.0.0"
    name: str
    description: str = ""
    schema_def: Dict[str, Any] = Field(default_factory=dict, alias="schema")
    category: ToolCategory = ToolCategory.GENERAL
    risk_level: RiskLevel = RiskLevel.LOW
    permissions: List[str] = Field(default_factory=list)
    environment: str = "host"  # host, browser, device, sandbox
    provider: str = "native"
    health_status: str = "HEALTHY"
    available: bool = True

    model_config = {"populate_by_name": True}


class CapabilityLease(BaseModel):
    """Time-bounded and scope-restricted lease for high-risk capabilities."""

    lease_id: str = Field(default_factory=lambda: f"lease-{uuid.uuid4().hex[:8]}")
    agent_id: str
    task_id: str
    capability: str
    scope: str = "global"  # specific path, domain, recipient, etc.
    max_calls: int = 1
    calls_used: int = 0
    created_at: float = Field(default_factory=time.time)
    expiration: float = Field(default_factory=lambda: time.time() + 600.0)  # default 10 min
    conditions: Dict[str, Any] = Field(default_factory=dict)
    approval_id: Optional[str] = None
    revoked: bool = False

    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if time.time() > self.expiration:
            return False
        if self.calls_used >= self.max_calls:
            return False
        return True
