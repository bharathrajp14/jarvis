# tests/adversarial/test_provider_adapters_chaos.py — Provider Adapter Chaos & Edge Cases Suite
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from backends.adapter import (
    AnthropicProviderAdapter,
    GeminiProviderAdapter,
    OllamaProviderAdapter,
    OpenAIProviderAdapter,
    ToolInvocation,
)


class MockFunctionCall:
    def __init__(self, name: str, args: dict | None):
        self.name = name
        self.args = args


class MockPart:
    def __init__(self, function_call: MockFunctionCall | None):
        self.function_call = function_call


class MockCandidate:
    def __init__(self, parts: list[MockPart]):
        self.content = MagicMock(parts=parts)


class MockGenerateContentResponse:
    def __init__(self, candidates: list[MockCandidate]):
        self.candidates = candidates


def test_gemini_adapter_chaos_and_parallel_calls():
    """Verify GeminiProviderAdapter handles single, multiple, and malformed function calls."""
    adapter = GeminiProviderAdapter()

    # 1. Single valid tool call
    mock_resp1 = MockGenerateContentResponse([
        MockCandidate([MockPart(MockFunctionCall("web_search", {"query": "pytest python"}))])
    ])

    invocations = adapter.extract_tool_calls(mock_resp1)
    assert len(invocations) == 1
    assert invocations[0].name == "web_search"
    assert invocations[0].arguments == {"query": "pytest python"}

    # 2. Parallel / Multiple tool calls in same response
    mock_resp_multi = MockGenerateContentResponse([
        MockCandidate([
            MockPart(MockFunctionCall("web_search", {"query": "pytest python"})),
            MockPart(MockFunctionCall("system_health", {})),
        ])
    ])

    multi_invocations = adapter.extract_tool_calls(mock_resp_multi)
    assert len(multi_invocations) == 2
    assert multi_invocations[0].name == "web_search"
    assert multi_invocations[1].name == "system_health"

    # 3. Malformed / None args fallback
    mock_resp_none = MockGenerateContentResponse([
        MockCandidate([MockPart(MockFunctionCall("open_app", None))])
    ])

    none_invocations = adapter.extract_tool_calls(mock_resp_none)
    assert len(none_invocations) == 1
    assert none_invocations[0].arguments == {}


def test_openai_adapter_parallel_calls_and_malformed_json():
    """Verify OpenAIProviderAdapter handles standard and parallel function calls."""
    adapter = OpenAIProviderAdapter()

    # 1. Parallel function calls
    mock_tool_1 = MagicMock()
    mock_tool_1.id = "call_abc123"
    mock_tool_1.function.name = "file_read"
    mock_tool_1.function.arguments = json.dumps({"path": "main.py"})

    mock_tool_2 = MagicMock()
    mock_tool_2.id = "call_def456"
    mock_tool_2.function.name = "fast_file_search"
    mock_tool_2.function.arguments = json.dumps({"query": "*.json"})

    mock_message = MagicMock(tool_calls=[mock_tool_1, mock_tool_2])
    mock_choice = MagicMock(message=mock_message)
    mock_response = MagicMock(choices=[mock_choice])

    invocations = adapter.extract_tool_calls(mock_response)
    assert len(invocations) == 2
    assert invocations[0].name == "file_read"
    assert invocations[0].arguments == {"path": "main.py"}
    assert invocations[1].name == "fast_file_search"
    assert invocations[1].arguments == {"query": "*.json"}

    # 2. Malformed JSON arguments
    mock_tool_bad = MagicMock()
    mock_tool_bad.id = "call_bad789"
    mock_tool_bad.function.name = "run_code"
    mock_tool_bad.function.arguments = "INVALID_JSON{{{"

    mock_resp_bad = MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[mock_tool_bad]))])
    bad_invocations = adapter.extract_tool_calls(mock_resp_bad)
    assert len(bad_invocations) == 1
    assert bad_invocations[0].arguments == {"raw_arguments": "INVALID_JSON{{{"}


def test_anthropic_adapter_tool_use_extraction():
    """Verify AnthropicProviderAdapter handles tool_use content blocks."""
    adapter = AnthropicProviderAdapter()

    mock_block1 = MagicMock()
    mock_block1.type = "tool_use"
    mock_block1.id = "toolu_01"
    mock_block1.name = "web_search"
    mock_block1.input = {"query": "anthropic claude"}
    mock_block2 = MagicMock(type="text", text="Searching the web now.")
    mock_response = MagicMock(content=[mock_block1, mock_block2])

    invocations = adapter.extract_tool_calls(mock_response)
    assert len(invocations) == 1
    assert invocations[0].name == "web_search"
    assert invocations[0].arguments == {"query": "anthropic claude"}
    assert invocations[0].call_id == "toolu_01"


def test_ollama_adapter_tool_use_extraction():
    """Verify OllamaProviderAdapter handles Ollama tool_calls dictionaries and objects."""
    adapter = OllamaProviderAdapter()

    mock_response = {
        "message": {
            "tool_calls": [
                {
                    "function": {
                        "name": "window_manager",
                        "arguments": {"action": "list"}
                    }
                }
            ]
        }
    }

    invocations = adapter.extract_tool_calls(mock_response)
    assert len(invocations) == 1
    assert invocations[0].name == "window_manager"
    assert invocations[0].arguments == {"action": "list"}
