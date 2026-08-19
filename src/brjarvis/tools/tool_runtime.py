# tools/tool_runtime.py — Tool Runtime Engine & Governance for JARVIS MK40.2 / MK41
"""
Authoritative Tool Runtime Engine for BR JARVIS.
Re-exports canonical domain models and delegates execution directly to Canonical ToolRuntime.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .domain import (
    RiskLevel,
    ToolCategory,
    ToolErrorCode,
    ToolExecutionStatus,
)
from .runtime import ToolRuntime, get_canonical_tool_runtime

logger = logging.getLogger("JARVIS.ToolRuntime")


class ToolRuntimeEngine:
    """
    Unified Tool Runtime Adapter maintaining backwards-compatibility
    while executing through the single authoritative ToolRuntime.
    """

    def __init__(self):
        self._runtime: ToolRuntime = get_canonical_tool_runtime()

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable[[Dict[str, Any]], Any],
        parameters: Optional[Dict[str, Any]] = None,
        is_read_only: bool = False,
        permission_required: str = "DEFAULT",
        risk_level: str = "LOW",
        category: str = "general",
        timeout_sec: float = 30.0,
    ) -> None:
        """Register a tool in the canonical runtime."""
        cat_enum = ToolCategory.GENERAL
        try:
            cat_enum = ToolCategory(category.lower())
        except Exception:
            pass

        risk_enum = RiskLevel.LOW
        try:
            risk_enum = RiskLevel(risk_level.lower())
        except Exception:
            pass

        self._runtime.register_tool(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters,
            category=cat_enum,
            risk_level=risk_enum,
            permission_required=permission_required,
            is_read_only=is_read_only,
            timeout_sec=timeout_sec,
        )

    async def execute_tool_async(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool asynchronously through canonical runtime."""
        res = await self._runtime.execute_tool_async(name, args)
        if not res.success and res.status in (ToolExecutionStatus.BLOCKED, ToolExecutionStatus.DENIED):
            raise PermissionError(res.error or f"Permission denied for tool '{name}'")
        if not res.success and res.error_code == ToolErrorCode.TOOL_NOT_FOUND:
            raise KeyError(f"Tool '{name}' is not registered in ToolRuntimeEngine")
        if not res.success and res.error_code == ToolErrorCode.SCHEMA_VALIDATION_ERR:
            raise ValueError(res.message)
        return res.data if res.data is not None else res.output

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool synchronously through canonical runtime."""
        res = self._runtime.execute_tool(name, args)
        if not res.success and res.status in (ToolExecutionStatus.BLOCKED, ToolExecutionStatus.DENIED):
            raise PermissionError(res.error or f"Permission denied for tool '{name}'")
        if not res.success and res.error_code == ToolErrorCode.TOOL_NOT_FOUND:
            raise KeyError(f"Tool '{name}' is not registered in ToolRuntimeEngine")
        if not res.success and res.error_code == ToolErrorCode.SCHEMA_VALIDATION_ERR:
            raise ValueError(res.message)
        return res.data if res.data is not None else res.output


_global_tool_runtime: Optional[ToolRuntimeEngine] = None


def get_tool_runtime() -> ToolRuntimeEngine:
    global _global_tool_runtime
    if _global_tool_runtime is None:
        _global_tool_runtime = ToolRuntimeEngine()
    return _global_tool_runtime
