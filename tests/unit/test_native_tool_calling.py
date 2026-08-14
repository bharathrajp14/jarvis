# tests/unit/test_native_tool_calling.py — ProviderAdapter Unit Tests
from __future__ import annotations

from types import SimpleNamespace
from backends.adapter import (
    GeminiProviderAdapter,
    OpenAIProviderAdapter,
    AnthropicProviderAdapter,
    ToolInvocation,
    get_provider_adapter,
)


def test_tool_invocation_validation():
    inv = ToolInvocation(tool_name="open_app", arguments={"app_name": "notepad"})
    assert inv.validate() is True
    assert inv.tool_name == "open_app"
    assert inv.arguments["app_name"] == "notepad"
    assert len(inv.call_id) > 0


def test_gemini_adapter_format_and_extract():
    adapter = GeminiProviderAdapter()
    schemas = [
        {
            "name": "system_status",
            "description": "Get CPU/RAM metrics",
            "parameters": {"type": "object", "properties": {}}
        }
    ]
    formatted = adapter.format_tools(schemas)
    assert len(formatted) == 1
    assert formatted[0]["function"]["name"] == "system_status"

    # Test extracting from OpenAI-compatible mock response
    mock_tc = SimpleNamespace(
        id="call_123",
        function=SimpleNamespace(name="system_status", arguments='{"detailed": true}')
    )
    mock_resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[mock_tc]))]
    )

    invocations = adapter.extract_tool_invocations(mock_resp)
    assert len(invocations) == 1
    assert invocations[0].tool_name == "system_status"
    assert invocations[0].arguments == {"detailed": True}
    assert invocations[0].call_id == "call_123"


def test_anthropic_adapter_format_and_extract():
    adapter = AnthropicProviderAdapter()
    schemas = [
        {
            "name": "file_read",
            "description": "Read file contents",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}
        }
    ]
    formatted = adapter.format_tools(schemas)
    assert len(formatted) == 1
    assert formatted[0]["name"] == "file_read"
    assert formatted[0]["input_schema"]["type"] == "object"

    # Test extracting tool_use block
    mock_block = SimpleNamespace(type="tool_use", id="tu_456", name="file_read", input={"path": "report.txt"})
    mock_resp = SimpleNamespace(content=[mock_block])

    invocations = adapter.extract_tool_invocations(mock_resp)
    assert len(invocations) == 1
    assert invocations[0].tool_name == "file_read"
    assert invocations[0].arguments == {"path": "report.txt"}
    assert invocations[0].call_id == "tu_456"


def test_provider_adapter_factory():
    assert isinstance(get_provider_adapter("gemini-2.5-flash"), GeminiProviderAdapter)
    assert isinstance(get_provider_adapter("claude-3-5-sonnet"), AnthropicProviderAdapter)
    assert isinstance(get_provider_adapter("gpt-4o"), OpenAIProviderAdapter)
    assert isinstance(get_provider_adapter("ollama/llama3"), OpenAIProviderAdapter)
