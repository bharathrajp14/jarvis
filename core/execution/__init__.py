# core/execution/__init__.py — Package exports for BR JARVIS Universal Execution Runtime
from __future__ import annotations

from core.execution.capability_checker import (
    CapabilityChecker,
    CapabilityStatus,
    get_capability_checker,
)
from core.execution.completion_gate import (
    GateEvaluationResult,
    TaskCompletionGate,
    get_task_completion_gate,
)
from core.execution.dependency_resolver import (
    DependencyCheckReport,
    DependencyResolver,
    get_dependency_resolver,
)
from core.execution.environment_resolver import (
    EnvironmentResolver,
    get_environment_resolver,
)
from core.execution.process_runner import (
    ProcessRunner,
    get_process_runner,
)
from core.execution.recovery_manager import (
    RecoveryManager,
    get_recovery_manager,
)
from core.execution.trace import (
    ExecutionTrace,
    TraceEvent,
)
from core.execution.types import (
    DependencyDeclaration,
    EnvironmentProfile,
    ExecutionResult,
    ExecutionStatus,
    RepairAction,
    RepairPolicy,
    RuntimeType,
    VerificationOutcome,
)
from core.execution.universal_runtime import (
    UniversalExecutionRuntime,
    get_universal_runtime,
)
from core.execution.verifier import (
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
