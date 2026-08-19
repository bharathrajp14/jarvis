# tests/test_canonical_tool_runtime.py — Verification Test Suite for Rebuilt Tool Runtime
"""
Comprehensive Verification Test Suite for BR JARVIS Canonical Tool Execution Platform.
Validates contracts, normalizer, validator, resolver, runtime lifecycle, and modernized tools.
"""

from __future__ import annotations

import asyncio

import pytest

from brjarvis.tools.domain import (
    RiskLevel,
    SideEffectLevel,
    ToolCategory,
    ToolDefinition,
    ToolErrorCode,
    ToolExecutionStatus,
)
from brjarvis.tools.normalizer import ArgumentNormalizer
from brjarvis.tools.resolver import ToolResolver
from brjarvis.tools.runtime import ToolRuntime
from brjarvis.tools.tool_result import ToolResult
from brjarvis.tools.validator import SchemaValidator

# ── 1. Domain & Contract Tests ────────────────────────────────────────────────


def test_tool_definition_contract():
    tool_def = ToolDefinition(
        name="test_tool",
        description="A test tool definition",
        category=ToolCategory.FILESYSTEM,
        risk_level=RiskLevel.MEDIUM,
        is_read_only=False,
    )
    assert tool_def.name == "test_tool"
    assert tool_def.tool_id == "filesystem.test_tool"
    assert tool_def.side_effect_level == SideEffectLevel.LOCAL_MUTATION
    model_schema = tool_def.to_model_schema()
    assert model_schema["name"] == "test_tool"


def test_tool_result_contract():
    res = ToolResult.success(
        tool_name="test_tool",
        data={"items": [1, 2, 3]},
        evidence="Observed 3 items in test",
        verified=True,
    )
    assert res.success is True
    assert res.is_verified is True
    assert res.status == ToolExecutionStatus.SUCCESS
    assert "Observed 3 items" in res.to_agent_str()
    d = res.to_dict()
    assert d["tool_name"] == "test_tool"
    assert d["success"] is True


def test_tool_result_failure_and_blocked():
    failed_res = ToolResult.failed(
        tool_name="failing_tool",
        error_code=ToolErrorCode.EXECUTION_EXCEPTION,
        message="Simulated error",
    )
    assert failed_res.success is False
    assert failed_res.status == ToolExecutionStatus.FAILED
    assert "[FAILED]" in failed_res.to_agent_str()

    blocked_res = ToolResult.blocked(
        tool_name="dangerous_tool",
        reason="Blocked by security policy",
    )
    assert blocked_res.is_blocked is True
    assert "[BLOCKED]" in blocked_res.to_agent_str()


# ── 2. Normalizer & Validator Tests ───────────────────────────────────────────


def test_argument_normalizer_booleans_and_paths():
    tool_def = ToolDefinition(
        name="sample_tool",
        description="Sample",
        parameters={
            "type": "object",
            "properties": {
                "recursive": {"type": "boolean", "default": False},
                "path": {"type": "string"},
                "url": {"type": "string"},
                "action": {"type": "string", "enum": ["READ", "WRITE"]},
            },
        },
    )

    raw_args = {
        "recursive": "true",
        "path": "workspace/Reports/doc.docx",
        "url": "google.com",
        "action": "read",
    }

    normalized = ArgumentNormalizer.normalize_args(tool_def, raw_args)
    assert normalized["recursive"] is True
    assert "workspace/workspace" not in normalized["path"]
    assert normalized["url"].startswith("https://")
    assert normalized["action"] == "READ"


def test_schema_validator_constraints():
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 2},
            "count": {"type": "integer", "minimum": 1, "maximum": 100},
            "category": {"type": "string", "enum": ["general", "system"]},
        },
        "required": ["query"],
    }

    # Valid
    valid, err = SchemaValidator.validate(schema, {"query": "hello", "count": 10, "category": "general"})
    assert valid is True
    assert err is None

    # Missing required
    valid, err = SchemaValidator.validate(schema, {"count": 10})
    assert valid is False
    assert "Missing required parameter 'query'" in err

    # Out of range
    valid, err = SchemaValidator.validate(schema, {"query": "test", "count": 500})
    assert valid is False
    assert "exceeds maximum" in err

    # Invalid enum
    valid, err = SchemaValidator.validate(schema, {"query": "test", "category": "unknown_cat"})
    assert valid is False
    assert "Invalid value" in err


# ── 3. Resolver Tests ─────────────────────────────────────────────────────────


def test_tool_resolver_namespace_and_aliases():
    catalog = {
        "file_read": ToolDefinition(name="file_read", description="Read file", tool_id="filesystem.read"),
        "browser_open_url": ToolDefinition(name="browser_open_url", description="Open browser", tool_id="browser.open"),
    }

    # Direct match
    t_def, err, code = ToolResolver.resolve("file_read", catalog)
    assert t_def is not None and t_def.name == "file_read"

    # Canonical namespace
    t_def, err, code = ToolResolver.resolve("filesystem.read", catalog)
    assert t_def is not None and t_def.name == "file_read"

    # Semantic alias
    t_def, err, code = ToolResolver.resolve("open_browser", catalog)
    assert t_def is not None and t_def.name == "browser_open_url"

    # Deprecation notice
    t_def, err, code = ToolResolver.resolve("file_controller", catalog)
    assert t_def is None
    assert "deprecated" in err.lower()


# ── 4. Canonical ToolRuntime Execution Tests ──────────────────────────────────


def test_runtime_execution_synchronous():
    runtime = ToolRuntime.get_instance()

    # Register custom verified handler
    def sample_add(args: dict) -> dict:
        a = args.get("a", 0)
        b = args.get("b", 0)
        return {"sum": a + b}

    runtime.register_tool(
        name="test_add_operation",
        description="Add two numbers",
        handler=sample_add,
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
        category=ToolCategory.GENERAL,
        risk_level=RiskLevel.LOW,
        permission_required="PUBLIC_READ",
        approval_required=False,
        is_read_only=True,
    )

    res = runtime.execute_tool("test_add_operation", {"a": 5, "b": 10})
    assert res.success is True
    assert res.data == {"sum": 15}
    assert res.verified is True


@pytest.mark.asyncio
async def test_runtime_execution_async_and_timeout():
    runtime = ToolRuntime.get_instance()

    async def slow_async_handler(args: dict) -> str:
        await asyncio.sleep(0.5)
        return "slow_done"

    runtime.register_tool(
        name="test_slow_tool",
        description="Simulated slow handler",
        handler=slow_async_handler,
        timeout_sec=0.1,  # Short timeout to force timeout status
        category=ToolCategory.GENERAL,
        risk_level=RiskLevel.LOW,
        permission_required="PUBLIC_READ",
        approval_required=False,
        is_read_only=True,
    )

    res = await runtime.execute_tool_async("test_slow_tool", {})
    assert res.status == ToolExecutionStatus.TIMEOUT
    assert res.error_code == ToolErrorCode.TIMEOUT_EXCEEDED


def test_runtime_registration_defaults_to_high_risk_approval():
    runtime = ToolRuntime.get_instance()
    tool_def = runtime.register_tool(
        name="test_incomplete_metadata_is_safe",
        description="A deliberately incomplete registration",
        handler=lambda args: "must not run without approval",
    )

    assert tool_def.risk_level == RiskLevel.HIGH
    assert tool_def.permission_required == "LOCAL_SYSTEM"
    assert tool_def.approval_required is True


# ── 5. Modernized Tool Suites Verification ────────────────────────────────────


def test_filesystem_suite_roundtrip():
    runtime = ToolRuntime.get_instance()

    # Ensure files tools are loaded
    import brjarvis.tools.file_tools  # noqa: F401

    test_file_name = "test_rebuilt_artifact.txt"
    test_content = "BR JARVIS Canonical Tool Rebuild Verified!\nTimestamped: 2026-08-16"

    # 1. Write file
    w_res = runtime.execute_tool("file_write", {"path": test_file_name, "content": test_content}, confirmed=True)
    assert w_res.success is True
    assert w_res.verified is True
    assert "SHA256" in w_res.evidence

    # 2. Read file
    r_res = runtime.execute_tool("file_read", {"path": test_file_name})
    assert r_res.success is True
    assert r_res.data == test_content
    assert r_res.verified is True

    # 3. List directory
    l_res = runtime.execute_tool("file_list", {"pattern": "*.txt"})
    assert l_res.success is True
    assert test_file_name in l_res.output

    # 4. Search file
    s_res = runtime.execute_tool("file_search", {"query": "Canonical Tool Rebuild"})
    assert s_res.success is True
    assert len(s_res.data) > 0

    # 5. Delete file
    d_res = runtime.execute_tool("file_delete", {"path": test_file_name, "permanent": True}, confirmed=True)
    assert d_res.success is True
    assert d_res.verified is True


def test_memory_suite_roundtrip():
    runtime = ToolRuntime.get_instance()
    import brjarvis.tools.memory_tools  # noqa: F401

    mem_name = "rebuild_verification_key"
    mem_content = "Universal ToolRuntime is fully operational with zero false successes."

    # 1. Save memory
    s_res = runtime.execute_tool(
        "memory_save",
        {
            "name": mem_name,
            "type": "project",
            "description": "Rebuild verification key",
            "content": mem_content,
            "scope": "project",
        },
        confirmed=True,
    )
    assert s_res.success is True
    assert s_res.verified is True

    # 2. Get memory
    g_res = runtime.execute_tool("memory_get", {"name": mem_name, "scope": "project"})
    assert g_res.success is True
    assert mem_content in g_res.data["content"]

    # 3. Search memory
    sr_res = runtime.execute_tool("memory_search", {"query": "Universal ToolRuntime", "max_results": 3})
    assert sr_res.success is True

    # 4. Delete memory
    del_res = runtime.execute_tool("memory_delete", {"name": mem_name, "scope": "project"}, confirmed=True)
    assert del_res.success is True


def test_code_sandbox_execution_fails_closed_without_isolation(monkeypatch):
    monkeypatch.delenv("JARVIS_ENABLE_UNSAFE_HOST_EXECUTION", raising=False)
    runtime = ToolRuntime.get_instance()
    import brjarvis.tools.code_tools  # noqa: F401

    code_snippet = "print('Hello from sandboxed canonical runtime!')"
    c_res = runtime.execute_tool("run_code", {"code": code_snippet, "lang": "python"}, confirmed=True)
    assert c_res.success is False
    assert "disabled" in (c_res.error or "").lower()


def test_tool_health_diagnostics():
    runtime = ToolRuntime.get_instance()
    import brjarvis.tools.diagnostics  # noqa: F401

    h_res = runtime.execute_tool("tool_health_check", {"run_smoke_tests": True}, confirmed=True)
    assert h_res.success is True
    assert h_res.data["total_tools"] >= 10
    smoke = h_res.data.get("smoke_tests", {})
    assert smoke.get("all_passed") is True, f"Smoke tests details: {smoke}"
