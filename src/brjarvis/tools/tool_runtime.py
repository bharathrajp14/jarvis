# tools/tool_runtime.py — Tool Runtime Engine & Governance for JARVIS MK37
from __future__ import annotations

import asyncio
import inspect
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from brjarvis.core.runtime import get_runtime
from brjarvis.events.bus import get_event_bus
from brjarvis.events.types import ToolExecutionEvent
from brjarvis.memory.unified_memory import get_unified_memory
from brjarvis.security.permissions import check_permission, evaluate_action_policy

logger = logging.getLogger("JARVIS.ToolRuntime")


class ToolExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    BLOCKED = "BLOCKED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_FOUND = "NOT_FOUND"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


@dataclass
class Observation:
    """Standardized physical state observation returned by tool execution."""
    subject: str
    state: str
    evidence: str = ""
    confidence: float = 1.0
    source: str = "tool_execution"
    timestamp: float = field(default_factory=time.time)


@dataclass
class ToolResult:
    """Canonical unified result contract returned by all tool invocations."""
    tool_name: str
    task_id: str = ""
    step_id: str = ""
    invocation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: ToolExecutionStatus = ToolExecutionStatus.SUCCESS
    data: Any = None
    error_code: Optional[str] = None
    message: str = ""
    evidence: str = ""
    execution_ms: float = 0.0
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    observation: Optional[Observation] = None

    @property
    def success(self) -> bool:
        return self.status == ToolExecutionStatus.SUCCESS

    @property
    def tool(self) -> str:
        return self.tool_name

    @property
    def execution_id(self) -> str:
        return self.invocation_id

    @property
    def output(self) -> Any:
        return self.data

    @property
    def error(self) -> str:
        return self.error_code or self.message

    @property
    def duration(self) -> float:
        return self.execution_ms / 1000.0

    @property
    def duration_ms(self) -> float:
        return self.execution_ms

    @property
    def verification(self) -> bool:
        return self.verified

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool": self.tool_name,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "invocation_id": self.invocation_id,
            "execution_id": self.invocation_id,
            "status": self.status.value,
            "success": self.success,
            "data": self.data,
            "output": self.data,
            "error_code": self.error_code,
            "error": self.error,
            "message": self.message,
            "evidence": self.evidence,
            "execution_ms": self.execution_ms,
            "duration": self.duration,
            "duration_ms": self.execution_ms,
            "verified": self.verified,
            "verification": self.verified,
            "metadata": self.metadata,
        }



@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_read_only: bool = False
    permission_required: str = "DEFAULT"
    risk_level: str = "LOW"
    timeout_sec: float = 30.0
    idempotent: bool = True
    parallel_safe: bool = True
    category: str = "General"


class ArgumentNormalizer:
    """Deterministic argument normalizer for paths, URLs, app names, booleans, and timeouts."""

    @classmethod
    def normalize_args(cls, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(args)
        for k, v in list(normalized.items()):
            if isinstance(v, str):
                v_str = v.strip()
                # Normalize boolean strings
                if v_str.lower() in ("true", "yes", "1"):
                    if k.startswith("is_") or k.startswith("use_") or k.endswith("_enabled") or k == "force":
                        normalized[k] = True
                elif v_str.lower() in ("false", "no", "0"):
                    if k.startswith("is_") or k.startswith("use_") or k.endswith("_enabled") or k == "force":
                        normalized[k] = False
                # Normalize path separators for filesystem args
                elif k in ("path", "file_path", "target_path", "dir_path", "source_path", "destination_path"):
                    normalized[k] = v_str.replace("\\", "/")
                # Normalize URL protocols
                elif k in ("url", "target_url", "link"):
                    if not v_str.startswith(("http://", "https://", "file://", "ws://", "wss://")):
                        if "." in v_str and not v_str.startswith("/"):
                            normalized[k] = f"https://{v_str}"
        return normalized


class ToolRuntimeEngine:

    """Universal Tool Runtime Engine with sandboxed execution, caching, permissions, and telemetry."""

    def __init__(self):
        self.runtime = get_runtime()
        self.event_bus = get_event_bus()
        self.memory = get_unified_memory()

        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._metrics: Dict[str, Dict[str, Any]] = {}

        # Register self in DI Container
        self.runtime.container.register_instance(ToolRuntimeEngine, self)
        logger.info("⚡ ToolRuntimeEngine initialized")

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable[[Dict[str, Any]], Any],
        parameters: Optional[Dict[str, Any]] = None,
        is_read_only: bool = False,
        permission_required: str = "DEFAULT",
    ) -> None:
        """Register a tool definition and handler function."""
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters or {},
            is_read_only=is_read_only,
            permission_required=permission_required,
        )
        self._tools[name] = tool_def
        self._handlers[name] = handler
        logger.debug(f"ToolRuntime: Registered tool '{name}' (Read-only: {is_read_only})")

    async def execute_tool_async(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool asynchronously with permission validation, caching, and telemetry."""
        if name not in self._tools or name not in self._handlers:
            raise KeyError(f"Tool '{name}' is not registered in ToolRuntimeEngine")

        tool_def = self._tools[name]
        handler = self._handlers[name]

        # 0. Deterministic Argument Normalization
        args = ArgumentNormalizer.normalize_args(name, args)

        # 1. Security & Permission Validation

        if not check_permission(tool_def.permission_required, args):
            err_msg = f"Permission denied for tool '{name}' (Action: {tool_def.permission_required})"
            logger.warning(f"🔒 {err_msg}")
            raise PermissionError(err_msg)

        # 1b. Prompt Injection Security Audit for untrusted input parameters
        try:
            from brjarvis.guardian.prompt_injection_shield import check_prompt_injection
            for arg_k, arg_v in args.items():
                if isinstance(arg_v, str) and len(arg_v) > 20:
                    is_injected, reason = check_prompt_injection(arg_v)
                    if is_injected:
                        logger.warning(f"🛡️ Security Alert: Injection detected in tool '{name}' arg '{arg_k}': {reason}")
                        raise ValueError(f"Security Alert: Prompt injection pattern detected in argument '{arg_k}'")
        except ValueError:
            raise
        except Exception:
            pass

        # 2. Result Caching for Read-Only Tools
        if tool_def.is_read_only:
            cached_res = self.memory.get_cached_tool_result(name, args)
            if cached_res is not None:
                logger.debug(f"⚡ Tool Cache Hit for '{name}'")
                return cached_res

        # 3. Telemetry Start Event
        t0 = time.perf_counter()
        self.event_bus.publish(ToolExecutionEvent(
            topic="tool.exec.start",
            tool_name=name,
            args=args,
        ))

        try:
            # 4. Handler Execution
            if inspect.iscoroutinefunction(handler):
                result = await handler(args)
            else:
                result = handler(args)

            duration_ms = (time.perf_counter() - t0) * 1000.0

            # 5. Cache Save if Read-Only
            if tool_def.is_read_only and result is not None:
                self.memory.cache_tool_result(name, args, result, ttl=180.0)

            # Record telemetry metrics
            m = self._metrics.setdefault(name, {"calls": 0, "successes": 0, "failures": 0, "total_duration_ms": 0.0})
            m["calls"] += 1
            m["successes"] += 1
            m["total_duration_ms"] += duration_ms

            # 6. Telemetry Completion Event
            self.event_bus.publish(ToolExecutionEvent(
                topic="tool.exec.completed",
                tool_name=name,
                args=args,
                success=True,
                result=result,
                duration_ms=duration_ms,
            ))

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.error(f"❌ Tool '{name}' execution error: {e}", exc_info=True)
            m = self._metrics.setdefault(name, {"calls": 0, "successes": 0, "failures": 0, "total_duration_ms": 0.0})
            m["calls"] += 1
            m["failures"] += 1
            m["total_duration_ms"] += duration_ms

            self.event_bus.publish(ToolExecutionEvent(
                topic="tool.exec.failed",
                tool_name=name,
                args=args,
                success=False,
                result=str(e),
                duration_ms=duration_ms,
            ))
            raise

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool synchronously returning the actual result payload."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(self.execute_tool_async(name, args), loop)
            return future.result(timeout=60.0)
        except RuntimeError:
            return asyncio.run(self.execute_tool_async(name, args))

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tool definitions."""
        return list(self._tools.values())


_global_tool_runtime: Optional[ToolRuntimeEngine] = None

# Canonical alias for ToolRuntimeEngine
ToolRuntime = ToolRuntimeEngine


def get_tool_runtime() -> ToolRuntimeEngine:
    global _global_tool_runtime
    if _global_tool_runtime is None:
        _global_tool_runtime = ToolRuntimeEngine()
    return _global_tool_runtime
