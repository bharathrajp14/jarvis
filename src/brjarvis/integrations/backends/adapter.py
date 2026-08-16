# backends/adapter.py — Native Structured Provider Tool Adapter Subsystem
"""
Universal ProviderAdapter layer for BR JARVIS MK40.
Normalizes native tool/function calling across Gemini, OpenAI, Anthropic, and Ollama,
eliminating brittle regex and markdown JSON parsing from orchestrator loops.
"""
from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("JARVIS.ProviderAdapter")


@dataclass
class ToolInvocation:
    """Normalized provider-agnostic tool invocation record."""
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_call: Any = None

    @property
    def name(self) -> str:
        return self.tool_name

    def validate(self) -> bool:
        """Verify invocation structure integrity."""
        return bool(self.tool_name and isinstance(self.arguments, dict))


class BaseProviderAdapter(ABC):
    """Abstract interface for provider-specific structured tool formatting and parsing."""

    @abstractmethod
    def format_tools(self, tool_schemas: List[Dict[str, Any]]) -> Any:
        """Convert standard tool schemas into provider-native tool format."""
        pass

    @abstractmethod
    def extract_tool_invocations(self, response: Any) -> List[ToolInvocation]:
        """Extract normalized ToolInvocation instances from provider response object."""
        pass

    def extract_tool_calls(self, response: Any) -> List[ToolInvocation]:
        """Alias for extract_tool_invocations."""
        return self.extract_tool_invocations(response)

    @abstractmethod
    def format_tool_result_message(self, invocation: ToolInvocation, result: Any) -> Dict[str, Any]:
        """Format a tool result into the provider's native conversation message format."""
        pass


class GeminiProviderAdapter(BaseProviderAdapter):
    """Google Gemini native function calling adapter (genai SDK & Proxy Brain)."""

    def format_tools(self, tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format schemas for Google GenAI / OpenAI-compat gateway."""
        formatted = []
        for s in tool_schemas:
            name = s.get("name", "")
            desc = s.get("description", "")
            params = s.get("parameters") or {"type": "object", "properties": {}}
            formatted.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": params,
                }
            })
        return formatted

    def extract_tool_invocations(self, response: Any) -> List[ToolInvocation]:
        """Extract tool calls from Gemini response (object or ProxyBrain completion choice)."""
        invocations: List[ToolInvocation] = []

        if response is None:
            return invocations

        # 1. Check if OpenAI-compatible choice response
        choices = getattr(response, "choices", None)
        if isinstance(choices, (list, tuple)) and choices:
            msg = getattr(choices[0], "message", None)
            tool_calls = getattr(msg, "tool_calls", None) if msg else None
            if isinstance(tool_calls, (list, tuple)) and tool_calls:
                for tc in tool_calls:
                    fn = getattr(tc, "function", None)
                    name = str(getattr(fn, "name", ""))
                    raw_args = getattr(fn, "arguments", {})
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
                    except Exception:
                        args = {}
                    invocations.append(ToolInvocation(
                        tool_name=name,
                        arguments=args,
                        call_id=str(getattr(tc, "id", str(uuid.uuid4()))),
                        raw_call=tc,
                    ))
                return invocations

        # 2. Check if dict response with tool_calls
        if isinstance(response, dict):
            msg = response.get("message", response)
            tool_calls = msg.get("tool_calls", response.get("tool_calls"))
            if isinstance(tool_calls, list):
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = str(fn.get("name", ""))
                    raw_args = fn.get("arguments", {})
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
                    except Exception:
                        args = {}
                    invocations.append(ToolInvocation(
                        tool_name=name,
                        arguments=args,
                        call_id=str(tc.get("id", str(uuid.uuid4()))),
                        raw_call=tc,
                    ))
                return invocations

        # 3. Check Google genai.types GenerateContentResponse
        f_calls = getattr(response, "function_calls", None)
        if isinstance(f_calls, (list, tuple)) and f_calls:
            for fc in f_calls:
                name = str(getattr(fc, "name", ""))
                args = getattr(fc, "args", {})
                invocations.append(ToolInvocation(
                    tool_name=name,
                    arguments=dict(args or {}) if args is not None else {},
                    raw_call=fc,
                ))
            if invocations:
                return invocations

        candidates = getattr(response, "candidates", None)
        if candidates and isinstance(candidates, (list, tuple)):
            for cand in candidates:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts and isinstance(parts, (list, tuple)):
                    for part in parts:
                        fc = getattr(part, "function_call", None)
                        if fc and getattr(fc, "name", None):
                            name = str(getattr(fc, "name"))
                            raw_args = getattr(fc, "args", {})
                            invocations.append(ToolInvocation(
                                tool_name=name,
                                arguments=dict(raw_args or {}) if raw_args is not None else {},
                                raw_call=fc,
                            ))

        return invocations

    def format_tool_result_message(self, invocation: ToolInvocation, result: Any) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": invocation.call_id,
            "name": invocation.tool_name,
            "content": str(result),
        }


class OpenAIProviderAdapter(BaseProviderAdapter):
    """OpenAI / OpenAI-compatible endpoint native function calling adapter."""

    def format_tools(self, tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": s.get("name", ""),
                    "description": s.get("description", ""),
                    "parameters": s.get("parameters", {"type": "object", "properties": {}}),
                }
            }
            for s in tool_schemas
        ]

    def extract_tool_invocations(self, response: Any) -> List[ToolInvocation]:
        invocations: List[ToolInvocation] = []
        if not response:
            return invocations

        if hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    fn = tc.function
                    raw_args = getattr(fn, "arguments", {})
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
                    except Exception:
                        args = {"raw_arguments": raw_args}
                    invocations.append(ToolInvocation(
                        tool_name=getattr(fn, "name", ""),
                        arguments=args,
                        call_id=getattr(tc, "id", str(uuid.uuid4())),
                        raw_call=tc,
                    ))
            return invocations

        if isinstance(response, dict):
            msg = response.get("message", response)
            tool_calls = msg.get("tool_calls", response.get("tool_calls"))
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    raw_args = fn.get("arguments", {})
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
                    except Exception:
                        args = {"raw_arguments": raw_args}
                    invocations.append(ToolInvocation(
                        tool_name=name,
                        arguments=args,
                        call_id=tc.get("id", str(uuid.uuid4())),
                        raw_call=tc,
                    ))
                return invocations

        return invocations

    def format_tool_result_message(self, invocation: ToolInvocation, result: Any) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": invocation.call_id,
            "name": invocation.tool_name,
            "content": str(result),
        }


class AnthropicProviderAdapter(BaseProviderAdapter):
    """Anthropic Claude tool use adapter."""

    def format_tools(self, tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.get("name", ""),
                "description": s.get("description", ""),
                "input_schema": s.get("parameters", {"type": "object", "properties": {}}),
            }
            for s in tool_schemas
        ]

    def extract_tool_invocations(self, response: Any) -> List[ToolInvocation]:
        invocations: List[ToolInvocation] = []
        content = getattr(response, "content", None)
        if isinstance(content, list):
            for block in content:
                b_type = getattr(block, "type", "") if not isinstance(block, dict) else block.get("type", "")
                if b_type == "tool_use":
                    b_name = getattr(block, "name", "") if not isinstance(block, dict) else block.get("name", "")
                    b_input = getattr(block, "input", {}) if not isinstance(block, dict) else block.get("input", {})
                    b_id = getattr(block, "id", "") if not isinstance(block, dict) else block.get("id", "")
                    invocations.append(ToolInvocation(
                        tool_name=str(b_name),
                        arguments=dict(b_input or {}),
                        call_id=str(b_id) if b_id else str(uuid.uuid4()),
                        raw_call=block,
                    ))
        return invocations

    def format_tool_result_message(self, invocation: ToolInvocation, result: Any) -> Dict[str, Any]:
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": invocation.call_id,
                    "content": str(result),
                }
            ]
        }


class OllamaProviderAdapter(OpenAIProviderAdapter):
    """Ollama local models native tool adapter (OpenAI schema format)."""
    pass


# ── Registry & Factory ────────────────────────────────────────────────────────

_ADAPTERS: Dict[str, BaseProviderAdapter] = {
    "gemini": GeminiProviderAdapter(),
    "openai": OpenAIProviderAdapter(),
    "openai_compat": OpenAIProviderAdapter(),
    "anthropic": AnthropicProviderAdapter(),
    "claude": AnthropicProviderAdapter(),
    "ollama": OllamaProviderAdapter(),
}


def get_provider_adapter(provider_name: str) -> BaseProviderAdapter:
    """Retrieve the appropriate ProviderAdapter for a given model/provider name."""
    norm = provider_name.lower().strip()
    if "gemini" in norm:
        return _ADAPTERS["gemini"]
    elif "anthropic" in norm or "claude" in norm:
        return _ADAPTERS["anthropic"]
    elif "ollama" in norm:
        return _ADAPTERS["ollama"]
    return _ADAPTERS.get(norm, _ADAPTERS["openai_compat"])
