# core/execution/__init__.py — Package exports for BR JARVIS Universal Execution Runtime
from __future__ import annotations

from .capability_checker import (
    CapabilityChecker,
    CapabilityStatus,
    get_capability_checker,
)
from .completion_gate import (
    GateEvaluationResult,
    TaskCompletionGate,
    get_task_completion_gate,
)
from .dependency_resolver import (
    DependencyCheckReport,
    DependencyResolver,
    get_dependency_resolver,
)
from .environment_resolver import (
    EnvironmentResolver,
    get_environment_resolver,
)
from .process_runner import (
    ProcessRunner,
    get_process_runner,
)
from .recovery_manager import (
    RecoveryManager,
    get_recovery_manager,
)
from .trace import (
    ExecutionTrace,
    TraceEvent,
)
from .types import (
    DependencyDeclaration,
    EnvironmentProfile,
    ExecutionResult,
    ExecutionStatus,
    RepairAction,
    RepairPolicy,
    RuntimeType,
    VerificationOutcome,
)
from .universal_runtime import (
    UniversalExecutionRuntime,
    get_universal_runtime,
)
from .verifier import (
    ApplicationVerifier,
    BrowserVerifier,
    DirectoryVerifier,
    DocumentVerifier,
    FileVerifier,
    OutputContractValidator,
    UniversalVerifier,
    get_universal_verifier,
)

__all__ = [
    "UniversalExecutionRuntime",
    "get_universal_runtime",
    "EnvironmentResolver",
    "get_environment_resolver",
    "DependencyResolver",
    "get_dependency_resolver",
    "CapabilityChecker",
    "get_capability_checker",
    "ProcessRunner",
    "get_process_runner",
    "UniversalVerifier",
    "get_universal_verifier",
    "RecoveryManager",
    "get_recovery_manager",
    "TaskCompletionGate",
    "get_task_completion_gate",
    "ExecutionTrace",
    "TraceEvent",
    "ExecutionStatus",
    "ExecutionResult",
    "EnvironmentProfile",
    "DependencyDeclaration",
    "RepairPolicy",
    "RepairAction",
    "RuntimeType",
    "VerificationOutcome",
    "CapabilityStatus",
    "DependencyCheckReport",
    "GateEvaluationResult",
    "FileVerifier",
    "DirectoryVerifier",
    "DocumentVerifier",
    "ApplicationVerifier",
    "BrowserVerifier",
    "OutputContractValidator",
]
