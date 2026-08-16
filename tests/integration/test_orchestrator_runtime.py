"""Integration tests for Assistant Runtime & Orchestrator Dispatch."""
from __future__ import annotations

import pytest
from brjarvis.core.bootstrap import build_assistant_runtime


@pytest.mark.integration
def test_build_assistant_runtime():
    """Verify runtime container instantiates all core engines."""
    runtime = build_assistant_runtime()
    assert runtime is not None
    assert hasattr(runtime, "orchestrator")
    assert hasattr(runtime, "memory")
    assert hasattr(runtime, "tools")
    assert hasattr(runtime, "event_bus")


@pytest.mark.integration
def test_orchestrator_command_execution():
    """Verify orchestrator handles basic queries and intent routing."""
    runtime = build_assistant_runtime()
    res = runtime.orchestrator.handle_query("System status check")
    assert res is not None
    assert "status" in str(res).lower() or "ok" in str(res).lower() or isinstance(res, dict)
