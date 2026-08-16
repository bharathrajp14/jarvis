# core/execution/types.py — Data Contracts for BR JARVIS Universal Execution Runtime
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ExecutionStatus(str, Enum):
    """Canonical lifecycle status for any execution unit in BR JARVIS."""
    SUCCESS_VERIFIED       = "SUCCESS_VERIFIED"
    SUCCESS_UNVERIFIED     = "SUCCESS_UNVERIFIED"
    PARTIAL_SUCCESS        = "PARTIAL_SUCCESS"
    FAILED                 = "FAILED"
    MISSING_DEPENDENCY     = "MISSING_DEPENDENCY"
    ENVIRONMENT_ERROR      = "ENVIRONMENT_ERROR"
    CONFIGURATION_ERROR    = "CONFIGURATION_ERROR"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    PERMISSION_DENIED      = "PERMISSION_DENIED"
    TIMEOUT                = "TIMEOUT"
    CANCELLED              = "CANCELLED"
    BLOCKED                = "BLOCKED"
    RECOVERY_FAILED        = "RECOVERY_FAILED"
    NOT_IMPLEMENTED        = "NOT_IMPLEMENTED"
    VERIFICATION_FAILED    = "VERIFICATION_FAILED"

    @property
    def is_success(self) -> bool:
        return self in (ExecutionStatus.SUCCESS_VERIFIED, ExecutionStatus.SUCCESS_UNVERIFIED)

    @property
    def is_verified_success(self) -> bool:
        return self == ExecutionStatus.SUCCESS_VERIFIED


class ApplicationStatus(str, Enum):
    """Explicit multi-level lifecycle status for desktop applications and document viewers."""
    LAUNCH_NOT_ATTEMPTED = "LAUNCH_NOT_ATTEMPTED"
    LAUNCH_REQUESTED     = "LAUNCH_REQUESTED"
    PROCESS_STARTED      = "PROCESS_STARTED"
    WINDOW_FOUND         = "WINDOW_FOUND"
    APPLICATION_READY    = "APPLICATION_READY"
    DOCUMENT_LOADED      = "DOCUMENT_LOADED"
    OPEN_VERIFIED        = "OPEN_VERIFIED"
    OPEN_FAILED          = "OPEN_FAILED"


class RepairPolicy(str, Enum):
    """Governance policy for automated runtime repair."""
    AUTO_REPAIR_SAFE   = "AUTO_REPAIR_SAFE"
    ASK_BEFORE_REPAIR  = "ASK_BEFORE_REPAIR"
    NO_AUTO_REPAIR     = "NO_AUTO_REPAIR"


class RuntimeType(str, Enum):
    """Supported execution environments."""
    PYTHON      = "python"
    NODE        = "node"
    POWERSHELL  = "powershell"
    BASH        = "bash"
    GIT         = "git"
    BROWSER     = "browser"
    SYSTEM_CLI  = "system_cli"
    OLLAMA      = "ollama"
    DOCKER      = "docker"
    UNKNOWN     = "unknown"


@dataclass
class EnvironmentProfile:
    """Detailed profile of a resolved runtime environment."""
    runtime_type: RuntimeType = RuntimeType.PYTHON
    executable: str = ""
    version: str = ""
    is_virtualenv: bool = False
    virtualenv_path: Optional[str] = None
    project_root: str = ""
    working_directory: str = ""
    precedence_tier: int = 5  # 1 (explicit) to 6 (global fallback)
    precedence_source: str = "system"
    env_vars: Dict[str, str] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    is_healthy: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runtime_type": self.runtime_type.value,
            "executable": self.executable,
            "version": self.version,
            "is_virtualenv": self.is_virtualenv,
            "virtualenv_path": self.virtualenv_path,
            "project_root": self.project_root,
            "working_directory": self.working_directory,
            "precedence_tier": self.precedence_tier,
            "precedence_source": self.precedence_source,
            "capabilities": self.capabilities,
            "is_healthy": self.is_healthy,
            "notes": self.notes,
        }


@dataclass
class DependencyDeclaration:
    """Machine-readable dependency contract for a tool or execution step."""
    runtime: RuntimeType = RuntimeType.PYTHON
    min_runtime_version: Optional[str] = None
    packages: List[str] = field(default_factory=list)          # e.g. ["PyMuPDF", "python-docx"]
    import_names: List[str] = field(default_factory=list)      # e.g. ["fitz", "docx"]
    executables: List[str] = field(default_factory=list)       # e.g. ["git", "node", "pwsh"]
    browser_binaries: List[str] = field(default_factory=list)  # e.g. ["chromium"]
    files: List[str] = field(default_factory=list)             # e.g. ["config/template.docx"]
    directories: List[str] = field(default_factory=list)       # e.g. ["workspace/Documents"]
    services: List[str] = field(default_factory=list)          # e.g. ["ollama"]
    credentials: List[str] = field(default_factory=list)       # e.g. ["GEMINI_API_KEY"]
    env_vars: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["runtime"] = self.runtime.value
        return d


@dataclass
class VerificationOutcome:
    """Outcome of real-world physical side-effect verification."""
    verified: bool = False
    verifier_name: str = "GenericVerifier"
    status: ExecutionStatus = ExecutionStatus.FAILED
    evidence: str = ""
    details: str = ""
    error: Optional[str] = None
    observed_state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "verifier_name": self.verifier_name,
            "status": self.status.value,
            "evidence": self.evidence,
            "details": self.details,
            "error": self.error,
            "observed_state": self.observed_state,
            "timestamp": self.timestamp,
        }


@dataclass
class RepairAction:
    """Action description for auto-repairing runtime or dependency failures."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: str = "install_package"  # install_package, install_browser, create_dir, etc.
    description: str = ""
    command: List[str] = field(default_factory=list)
    target_environment: Optional[EnvironmentProfile] = None
    risk_level: str = "LOW"  # SAFE, CONFIRMATION, FORBIDDEN
    executed: bool = False
    success: bool = False
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.target_environment:
            d["target_environment"] = self.target_environment.to_dict()
        return d


@dataclass
class ExecutionResult:
    """Canonical universal result structure returned by all tool, code, and process executions."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    status: ExecutionStatus = ExecutionStatus.SUCCESS_VERIFIED
    tool_or_command: str = ""
    runtime: Optional[EnvironmentProfile] = None
    executable: str = ""
    cwd: str = ""
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    output: Any = None
    evidence: str = ""
    verification: Optional[VerificationOutcome] = None
    recovery: Optional[RepairAction] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    host_artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def success(self) -> bool:
        return self.status.is_success

    @property
    def verified(self) -> bool:
        return self.status.is_verified_success

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "success": self.success,
            "verified": self.verified,
            "tool_or_command": self.tool_or_command,
            "runtime": self.runtime.to_dict() if self.runtime else None,
            "executable": self.executable,
            "cwd": self.cwd,
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "output": self.output,
            "evidence": self.evidence,
            "verification": self.verification.to_dict() if self.verification else None,
            "recovery": self.recovery.to_dict() if self.recovery else None,
            "artifacts": self.artifacts,
            "host_artifacts": self.host_artifacts,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
