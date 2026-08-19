# src/brjarvis/contracts/agent.py — Canonical Agent Contracts for BR JARVIS
"""
Canonical Agent contracts for BR JARVIS operating runtime.
Defines AgentRole, AgentRequest, AgentResponse, and AgentDefinition.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Canonical Agent Roles in BR JARVIS."""
    GENERAL = "general"
    CODING = "coding"
    RESEARCH = "research"
    BROWSER = "browser"
    DESKTOP = "desktop"
    VOICE = "voice"
    REVIEWER = "reviewer"
    MANAGER = "manager"


class AgentRequest(BaseModel):
    """Canonical incoming request to an agent."""
    request_id: str = Field(default_factory=lambda: f"req-{uuid.uuid4().hex[:10]}")
    session_id: str = Field(default="default_session")
    user_id: str = Field(default="default_user")
    agent_id: str = Field(default="jarvis-general")
    role: AgentRole = Field(default=AgentRole.GENERAL)
    query: str = Field(..., description="User prompt or task instruction")
    modality: str = Field(default="text", description="text, voice, vision, automated")
    context: Dict[str, Any] = Field(default_factory=dict, description="Injected context payload")
    task_id: Optional[str] = None
    project_id: str = Field(default="global")
    workspace_id: str = Field(default="default")
    model_policy: Dict[str, Any] = Field(default_factory=dict)
    budget_policy: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class AgentResponse(BaseModel):
    """Canonical output from an agent execution turn."""
    response_id: str = Field(default_factory=lambda: f"resp-{uuid.uuid4().hex[:10]}")
    request_id: str = Field(...)
    session_id: str = Field(...)
    agent_id: str = Field(default="jarvis-general")
    text: str = Field(default="", description="Synthesized textual response")
    status: str = Field(default="completed", description="completed, partial, failed, waiting_approval")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    verification_results: List[Dict[str, Any]] = Field(default_factory=list)
    effect_receipts: List[Dict[str, Any]] = Field(default_factory=list)
    handoff: Optional[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    usage: Dict[str, int] = Field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    latency_ms: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class AgentDefinition(BaseModel):
    """Specification and capability boundaries of an Agent Role."""
    agent_id: str
    role: AgentRole
    name: str
    description: str = ""
    instructions: str = ""
    skills: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    model_policy: Dict[str, Any] = Field(default_factory=dict)
    budget_policy: Dict[str, Any] = Field(default_factory=dict)
    workspace_policy: Dict[str, Any] = Field(default_factory=dict)
    evaluation_policy: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
