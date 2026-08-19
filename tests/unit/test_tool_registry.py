"""Unit tests for Dynamic Tool Registry & Validation."""

from __future__ import annotations

import pytest

from brjarvis.tools.registry import TOOL_REGISTRY, TOOL_SCHEMAS, _import_plugins, execute_tool, register_tool


@pytest.mark.unit
def test_global_tool_registry_active_count():
    """Verify tool registry contains active tools after full plugin load."""
    _import_plugins(full=True)
    assert len(TOOL_REGISTRY) >= 100
    assert len(TOOL_SCHEMAS) >= 100


@pytest.mark.unit
def test_tool_registration_and_execution():
    """Verify registering a custom test tool and executing it."""

    @register_tool(
        name="calc_add_unit_test",
        description="Add two integers",
        risk_level="low",
        permission_required="PUBLIC_READ",
        approval_required=False,
        is_read_only=True,
    )
    def calc_add(params: dict) -> int:
        return params.get("a", 0) + params.get("b", 0)

    result = execute_tool("calc_add_unit_test", {"a": 5, "b": 7})
    assert int(result) == 12
