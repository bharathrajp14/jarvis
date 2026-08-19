# src/brjarvis/contracts/__init__.py — Central Canonical Contracts Export for BR JARVIS
"""
BR JARVIS MK40.2+ Canonical Contracts Package.
Exports all typed, serializable contracts across all architectural planes.
"""
from __future__ import annotations

from .agent import AgentDefinition, AgentRequest, AgentResponse, AgentRole
from .events import AgentEvent, EventEnvelope
from .memory import MemoryFeedbackRecord, MemoryQuery, MemoryRecord
from .model import ModelCapability, ModelHealth, ModelRequest, ModelResponse, ModelSelection
from .security import ActionDecision, IdentityScope, PermissionContext, SecretReference, SecurityDecision
from .session import Handoff, Session, SessionCheckpoint, SessionState, SessionTurn
from .task import ApprovalRequest, Task, TaskAction, TaskCriterion, TaskState, TaskStatus
from .tool import Capability, CapabilityLease, RiskLevel, ToolCategory, ToolRequest, ToolResult
from .verification import EffectReceipt, VerificationResult, VerificationStatus
from .workflow import WorkflowCheckpoint, WorkflowState, WorkflowStatus

__all__ = [
    # Agent
    "AgentRole",
    "AgentRequest",
    "AgentResponse",
    "AgentDefinition",
    # Task
    "TaskStatus",
    "TaskCriterion",
    "TaskAction",
    "ApprovalRequest",
    "Task",
    "TaskState",
    # Session
    "SessionState",
    "SessionTurn",
    "SessionCheckpoint",
    "Session",
    "Handoff",
    # Workflow
    "WorkflowStatus",
    "WorkflowCheckpoint",
    "WorkflowState",
    # Events
    "AgentEvent",
    "EventEnvelope",
    # Tool
    "ToolCategory",
    "RiskLevel",
    "ToolRequest",
    "ToolResult",
    "Capability",
    "CapabilityLease",
    # Model
    "ModelCapability",
    "ModelRequest",
    "ModelResponse",
    "ModelHealth",
    "ModelSelection",
    # Security
    "ActionDecision",
    "IdentityScope",
    "PermissionContext",
    "SecurityDecision",
    "SecretReference",
    # Memory
    "MemoryRecord",
    "MemoryQuery",
    "MemoryFeedbackRecord",
    # Verification
    "EffectReceipt",
    "VerificationStatus",
    "VerificationResult",
]
