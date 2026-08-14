# tools/tool_runtime.py — Tool Runtime Engine & Governance for JARVIS MK37
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from core.runtime import get_runtime
from events.bus import get_event_bus
from events.types import ToolExecutionEvent
from memory.unified_memory import get_unified_memory
from permissions import check_permission

logger = logging.getLogger("JARVIS.ToolRuntime")


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_read_only: bool = False
    permission_required: str = "DEFAULT"


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

        # 1. Security & Permission Validation
        if not check_permission(tool_def.permission_required, args):
            err_msg = f"Permission denied for tool '{name}' (Action: {tool_def.permission_required})"
            logger.warning(f"🔒 {err_msg}")
            raise PermissionError(err_msg)

        # 1b. RedTeam Prompt Injection Audit for untrusted input parameters
        try:
            from tools.redteam_tools import audit_prompt_security
            for arg_k, arg_v in args.items():
                if isinstance(arg_v, str) and len(arg_v) > 20:
                    sec_res = audit_prompt_security({"content": arg_v})
                    if isinstance(sec_res, str) and "INJECTION DETECTED" in sec_res:
                        logger.warning(f"🛡️ RedTeam Security Alert: Injection detected in tool '{name}' arg '{arg_k}'")
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


def get_tool_runtime() -> ToolRuntimeEngine:
    global _global_tool_runtime
    if _global_tool_runtime is None:
        _global_tool_runtime = ToolRuntimeEngine()
    return _global_tool_runtime
