# src/brjarvis/execution/__init__.py — Consolidated Master Execution Subsystem for BR JARVIS MK40.2+
from __future__ import annotations

from brjarvis.core.execution import (
    capability_checker,
    completion_gate,
    dependency_resolver,
    environment_resolver,
    process_runner,
    recovery_manager,
    trace,
    types,
    universal_runtime,
    verifier,
)
from brjarvis.core.execution.dependency_resolver import DependencyResolver
from brjarvis.core.execution.process_runner import ProcessRunner
from brjarvis.core.execution.universal_runtime import UniversalExecutionRuntime
from brjarvis.core.execution.verifier import UniversalVerifier

# Backward-compatibility aliases (old names that may be referenced externally)
UniversalRuntimeEngine = UniversalExecutionRuntime
UniversalActionVerifier = UniversalVerifier

__all__ = [
    "capability_checker",
    "completion_gate",
    "dependency_resolver",
    "environment_resolver",
    "process_runner",
    "recovery_manager",
    "trace",
    "types",
    "universal_runtime",
    "verifier",
    # Current names
    "UniversalExecutionRuntime",
    "UniversalVerifier",
    "ProcessRunner",
    "DependencyResolver",
    # Backward-compat aliases
    "UniversalRuntimeEngine",
    "UniversalActionVerifier",
]
