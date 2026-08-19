# src/brjarvis/tools/diagnostics.py — Tool Subsystem Diagnostics & Health Monitoring
"""
Tool Diagnostics and Capability Health Monitoring for BR JARVIS MK40.2 / MK41.
Inspects registration catalog, execution metrics, error rates, latencies, and provides smoke testing.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from .registry import register_tool
from .runtime import get_canonical_tool_runtime
from .tool_result import ToolResult

logger = logging.getLogger("JARVIS.Tools.Diagnostics")


class ToolDiagnostics:
    """Diagnostic inspector and health evaluator for the Tool subsystem."""

    @classmethod
    def get_catalog_health(cls) -> Dict[str, Any]:
        """Inspect all registered tools in the canonical catalog."""
        try:
            from .registry import _import_plugins

            _import_plugins(full=True)
        except Exception:
            pass

        runtime = get_canonical_tool_runtime()
        catalog = runtime.get_catalog()

        by_category: Dict[str, int] = {}
        by_risk: Dict[str, int] = {}
        read_only_count = 0
        approval_required_count = 0

        for t_def in catalog.values():
            cat = t_def.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

            risk = t_def.risk_level.value
            by_risk[risk] = by_risk.get(risk, 0) + 1

            if t_def.is_read_only:
                read_only_count += 1
            if t_def.approval_required:
                approval_required_count += 1

        return {
            "total_tools": len(catalog),
            "by_category": by_category,
            "by_risk_level": by_risk,
            "read_only_tools": read_only_count,
            "approval_required_tools": approval_required_count,
            "metrics": runtime._metrics,
            "timestamp": time.time(),
        }

    @classmethod
    def run_smoke_tests(cls) -> Dict[str, Any]:
        """Run safe non-destructive read-only smoke tests on foundational tools."""
        try:
            from .registry import _import_plugins

            _import_plugins(full=True)
        except Exception:
            pass

        runtime = get_canonical_tool_runtime()
        results: Dict[str, Any] = {}

        # 1. Test file_list
        res_list = runtime.execute_tool("file_list", {"path": "."}, confirmed=True)
        results["file_list"] = {
            "success": bool(res_list.is_success),
            "duration_ms": res_list.execution_ms,
            "evidence": res_list.evidence,
        }

        # 2. Test memory_search
        res_mem = runtime.execute_tool("memory_search", {"query": "system", "max_results": 1}, confirmed=True)
        results["memory_search"] = {
            "success": bool(res_mem.is_success),
            "duration_ms": res_mem.execution_ms,
            "evidence": res_mem.evidence,
        }

        # 3. Test list_calendar_events
        res_cal = runtime.execute_tool("list_calendar_events", {"days_ahead": 1}, confirmed=True)
        results["list_calendar_events"] = {
            "success": bool(res_cal.is_success),
            "duration_ms": res_cal.execution_ms,
            "evidence": res_cal.evidence,
        }

        all_passed = all(r["success"] is True for r in results.values())
        return {
            "all_passed": all_passed,
            "tests": results,
            "timestamp": time.time(),
        }


@register_tool(
    name="tool_health_check",
    description="Inspect tool catalog health, execution metrics, and run non-destructive smoke tests.",
    parameters={
        "type": "object",
        "properties": {
            "run_smoke_tests": {"type": "boolean", "description": "Whether to execute read-only smoke tests"}
        },
    },
    category="diagnostic",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_health_check(args: dict) -> ToolResult:
    """Tool health check endpoint."""
    run_smoke = bool(args.get("run_smoke_tests", False))
    health = ToolDiagnostics.get_catalog_health()

    if run_smoke:
        health["smoke_tests"] = ToolDiagnostics.run_smoke_tests()

    evidence = f"Tool Subsystem Health: {health['total_tools']} tools registered across {len(health['by_category'])} categories."
    return ToolResult.success(
        tool_name="tool_health_check",
        data=health,
        evidence=evidence,
        verified=True,
    )
