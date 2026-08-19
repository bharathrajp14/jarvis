# src/brjarvis/tools/domain.py — Canonical Tool Domain Model
"""
Canonical Tool Domain Model for BR JARVIS MK40.2 / MK41.
Defines first-class metadata, classification enums, observation structures, and tool definitions.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ToolExecutionStatus(str, Enum):
    """Authoritative execution status vocabulary for all tool invocations."""

    SUCCESS = "SUCCESS"  # Action executed and physically verified
    PARTIAL = "PARTIAL"  # Action partially executed or verified
    FAILED = "FAILED"  # Unrecoverable error during execution
    TIMEOUT = "TIMEOUT"  # Execution exceeded time budget
    BLOCKED = "BLOCKED"  # Security policy / sandbox blocked execution
    DENIED = "DENIED"  # Explicit policy denial
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"  # Paused pending human confirmation
    NOT_FOUND = "NOT_FOUND"  # Tool does not exist in catalog
    NOT_AVAILABLE = "NOT_AVAILABLE"  # Tool missing host dependencies
    UNSUPPORTED = "UNSUPPORTED"  # Tool unsupported on active OS
    CANCELLED = "CANCELLED"  # Cancelled by user or watchdog
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"  # Transitory network or resource conflict
    VERIFICATION_FAILED = "VERIFICATION_FAILED"  # Execution ran but post-state mismatch
    STATE_MISMATCH = "STATE_MISMATCH"  # Pre-condition check failed


class ToolCategory(str, Enum):
    """Categorical taxonomy for tool routing and capability discovery."""

    FILESYSTEM = "filesystem"
    BROWSER = "browser"
    DESKTOP = "desktop"
    SYSTEM = "system"
    COMMUNICATION = "communication"
    CODE = "code"
    DOCUMENT = "document"
    MEMORY = "memory"
    CAREER = "career"
    INTEGRATION = "integration"
    DIAGNOSTIC = "diagnostic"
    GENERAL = "general"


class RiskLevel(str, Enum):
    """Security and impact risk classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SideEffectLevel(str, Enum):
    """Classification of tool mutation potential."""

    READ_ONLY = "READ_ONLY"
    LOCAL_MUTATION = "LOCAL_MUTATION"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"
    DESTRUCTIVE = "DESTRUCTIVE"
    IRREVERSIBLE = "IRREVERSIBLE"


class VerificationStrategy(str, Enum):
    """Strategy used by the Verifier to confirm physical outcome."""

    NONE = "NONE"
    FILE_EXISTS = "FILE_EXISTS"
    FILE_CONTENT = "FILE_CONTENT"
    FILE_PARSED = "FILE_PARSED"
    FILE_ABSENT = "FILE_ABSENT"
    PROCESS_RUNNING = "PROCESS_RUNNING"
    WINDOW_ACTIVE = "WINDOW_ACTIVE"
    BROWSER_DOM = "BROWSER_DOM"
    READ_BACK_VALUE = "READ_BACK_VALUE"
    NETWORK_RESPONSE = "NETWORK_RESPONSE"


class CachePolicy(str, Enum):
    """Caching policy for read-only tools."""

    NO_CACHE = "NO_CACHE"
    CACHE_PER_ARGS = "CACHE_PER_ARGS"
    CACHE_SESSION = "CACHE_SESSION"


class ToolErrorCode(str, Enum):
    """Canonical error identifiers for machine-readable fault diagnosis."""

    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    SCHEMA_VALIDATION_ERR = "SCHEMA_VALIDATION_ERR"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    POLICY_DENIED = "POLICY_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
    EXECUTION_EXCEPTION = "EXECUTION_EXCEPTION"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    PATH_TRAVERSAL_BLOCKED = "PATH_TRAVERSAL_BLOCKED"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


@dataclass
class Observation:
    """Standardized physical state observation returned by tool execution."""

    subject: str  # Target entity (e.g. file URI, process name, window title)
    property: str = ""  # State property inspected (e.g. "exists", "volume_level", "text_content")
    old_state: Optional[Any] = None
    new_state: Optional[Any] = None
    evidence: str = ""  # Human/machine verifiable proof
    confidence: float = 1.0  # Confidence in observation [0.0 - 1.0]
    source: str = "tool_execution"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolDefinition:
    """
    First-class canonical metadata contract for all JARVIS tools.
    Never infer critical execution properties from arbitrary wrapper code.
    """

    name: str  # Primary invocation identifier (e.g. "file_write")
    description: str  # Complete model documentation
    tool_id: str = ""  # Namespaced ID (e.g. "filesystem.write")
    version: str = "1.0.0"
    category: ToolCategory = ToolCategory.GENERAL
    parameters: Dict[str, Any] = field(default_factory=dict)  # Input JSON Schema
    output_schema: Dict[str, Any] = field(default_factory=dict)

    # Security & Governance
    risk_level: RiskLevel = RiskLevel.HIGH
    permission_required: str = "LOCAL_SYSTEM"
    approval_required: bool = True

    # Execution Semantics
    is_read_only: bool = False
    idempotent: bool = True
    retryable: bool = True
    parallel_safe: bool = True
    side_effect_level: SideEffectLevel = SideEffectLevel.READ_ONLY

    # Limits & Execution Options
    timeout_sec: float = 30.0
    max_retries: int = 2
    supports_async: bool = False

    # Strategies & Resource Policies
    verification_strategy: VerificationStrategy = VerificationStrategy.NONE
    cache_policy: CachePolicy = CachePolicy.NO_CACHE
    cache_ttl_seconds: float = 180.0
    resource_reads: List[str] = field(default_factory=list)
    resource_writes: List[str] = field(default_factory=list)
    handler: Optional[Callable[..., Any]] = None

    def __post_init__(self):
        if not self.tool_id:
            self.tool_id = f"{self.category.value}.{self.name}"
        if self.is_read_only:
            self.side_effect_level = SideEffectLevel.READ_ONLY
            if self.cache_policy == CachePolicy.NO_CACHE:
                self.cache_policy = CachePolicy.CACHE_PER_ARGS
        elif self.side_effect_level == SideEffectLevel.READ_ONLY:
            self.side_effect_level = SideEffectLevel.LOCAL_MUTATION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tool_id": self.tool_id,
            "version": self.version,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "output_schema": self.output_schema,
            "risk_level": self.risk_level.value,
            "permission_required": self.permission_required,
            "approval_required": self.approval_required,
            "is_read_only": self.is_read_only,
            "idempotent": self.idempotent,
            "retryable": self.retryable,
            "parallel_safe": self.parallel_safe,
            "side_effect_level": self.side_effect_level.value,
            "timeout_sec": self.timeout_sec,
            "max_retries": self.max_retries,
            "supports_async": self.supports_async,
            "verification_strategy": self.verification_strategy.value,
            "cache_policy": self.cache_policy.value,
        }

    def to_model_schema(self) -> Dict[str, Any]:
        """Convert definition to OpenAI / Gemini compatible tool declaration dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
