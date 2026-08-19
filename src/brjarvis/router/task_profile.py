# router/task_profile.py — Request Profiling & Task Classification Engine
"""
Analyzes inbound user prompts, system instructions, and execution context to
generate a comprehensive 13-dimensional TaskProfile for model routing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("JARVIS.TaskProfile")


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskProfile:
    """13-dimensional semantic profile for model selection and scoring."""

    task_type: str = "chat"
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    requires_reasoning: bool = False
    requires_code: bool = False
    requires_tools: bool = False
    requires_agent: bool = False
    requires_vision: bool = False
    requires_structured_output: bool = False
    requires_image_gen: bool = False
    requires_long_context: bool = False
    latency_sensitive: bool = False
    risk_level: str = "low"
    context_size: int = 0
    expected_output_size: int = 1024
    explicit_provider: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Lexical detection patterns
_CODE_KEYWORDS = {
    "def ",
    "class ",
    "function",
    "import ",
    "const ",
    "let ",
    "var ",
    "return ",
    "async ",
    "await ",
    "lambda",
    "print(",
    "console.log",
    "dockerfile",
    "sql",
    "select ",
    "insert ",
    "update ",
    "delete ",
    "refactor",
    "bug",
    "traceback",
    "exception",
    "error",
    "nullpointer",
    "algorithm",
    "regex",
    "api",
    "endpoint",
    "pull request",
    "github",
}

_REASONING_KEYWORDS = {
    "analyze",
    "architecture",
    "tradeoff",
    "evaluate",
    "compare",
    "proof",
    "step-by-step",
    "why",
    "implication",
    "root cause",
    "deduce",
    "strategy",
    "philosophical",
    "deep reasoning",
    "audit",
    "security review",
    "vulnerability",
}

_AGENT_KEYWORDS = {
    "browse",
    "click",
    "open app",
    "automate",
    "navigate",
    "extract table",
    "download",
    "run script",
    "type",
    "press key",
    "search and summarize",
    "multi-step",
    "workflow",
    "execute task",
}

_FAST_GREETINGS = {
    "hi",
    "hello",
    "hey",
    "ping",
    "pong",
    "status",
    "test",
    "ok",
    "cool",
    "good morning",
    "good evening",
    "how are you",
    "who are you",
}


class TaskProfileClassifier:
    """Classifies user requests and context into structured TaskProfile."""

    @staticmethod
    def classify(
        messages: list[dict[str, Any]],
        system: str = "",
        tools: Optional[list[dict[str, Any]]] = None,
        requires_vision: bool = False,
        requires_image_gen: bool = False,
        json_mode: bool = False,
    ) -> TaskProfile:
        # Extract combined text
        all_text = " ".join([str(m.get("content", "")) for m in messages if isinstance(m, dict)] + [system])
        text_lower = all_text.lower().strip()
        word_count = len(text_lower.split())
        est_tokens = int(word_count * 1.3)

        # Base properties
        profile = TaskProfile(
            context_size=est_tokens,
            requires_vision=requires_vision,
            requires_image_gen=requires_image_gen,
            requires_structured_output=json_mode or ("return json" in text_lower or "valid json" in text_lower),
            requires_tools=bool(tools),
        )

        # 1. Vision & Image Gen
        if requires_image_gen or "generate image" in text_lower or "draw a " in text_lower:
            profile.task_type = "image_gen"
            profile.requires_image_gen = True
            profile.complexity = TaskComplexity.MEDIUM
            return profile

        if requires_vision or "screenshot" in text_lower or "ocr" in text_lower:
            profile.task_type = "vision"
            profile.requires_vision = True
            profile.complexity = TaskComplexity.MEDIUM
            return profile

        # 2. Fast Greetings / Short Latency-Sensitive Tasks
        if word_count < 6 and any(text_lower == g for g in _FAST_GREETINGS):
            profile.task_type = "fast_chat"
            profile.complexity = TaskComplexity.LOW
            profile.latency_sensitive = True
            profile.expected_output_size = 128
            return profile

        # 3. Agent & Tool Execution
        has_agent_keyword = any(k in text_lower for k in _AGENT_KEYWORDS)
        if tools or has_agent_keyword:
            profile.requires_tools = True
            if has_agent_keyword or len(tools or []) > 1:
                profile.requires_agent = True
                profile.task_type = "agent"
                profile.complexity = TaskComplexity.HIGH if word_count > 40 else TaskComplexity.MEDIUM
                return profile

        # 4. Code & Technical Tasks
        code_matches = sum(1 for k in _CODE_KEYWORDS if k in text_lower)
        if code_matches >= 2 or "```" in all_text:
            profile.requires_code = True
            profile.task_type = "code"
            if code_matches >= 4 or word_count > 100:
                profile.complexity = TaskComplexity.HIGH
                profile.requires_reasoning = True
            else:
                profile.complexity = TaskComplexity.MEDIUM
            return profile

        # 5. Deep Reasoning & Architecture
        reasoning_matches = sum(1 for k in _REASONING_KEYWORDS if k in text_lower)
        if reasoning_matches >= 2 or word_count > 250:
            profile.requires_reasoning = True
            profile.task_type = "reasoning"
            profile.complexity = TaskComplexity.HIGH if word_count > 100 else TaskComplexity.MEDIUM
            if word_count > 500:
                profile.complexity = TaskComplexity.CRITICAL
                profile.requires_long_context = True
            return profile

        # 6. Default General Conversation
        profile.task_type = "chat"
        profile.complexity = TaskComplexity.LOW if word_count < 25 else TaskComplexity.MEDIUM
        return profile
