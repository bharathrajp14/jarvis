# config/complexity_router.py — Multi-Dimensional Intelligent Complexity Analyzer for JARVIS MK37
"""
Advanced Semantic & Structural Complexity Analyzer.
Calculates a weighted complexity score S in [0, 100] based on 6 analytical signal vectors:
  1. Code & AST Syntax Density (operators, brackets, control flow, code fences)
  2. Cognitive Depth & Entropy (lexical diversity, average word length, analytical directives)
  3. Task Scope & Multi-Step Imperatives (numbered directives, sub-tasks, constraints)
  4. Prompt Length (non-linear scale)
  5. Dialogue History Depth & Accumulated Context
  6. Multimodal Vision Payload (base64, image URLs)

Complexity Tiers:
  - FAST   (Score < 15)  -> gemini-3-flash (Latency ~1.65s, max 256 tokens)
  - MEDIUM (15 <= Score < 50) -> gemini-3.6-flash-high (Latency ~1.82s, max 2048 tokens)
  - HIGH   (Score >= 50) -> gemini-3.1-pro-high (Latency ~5.63s, max 8192 tokens)
  - VISION (Multimodal)  -> gemini-3.1-flash-image (max 4096 tokens)
"""
from __future__ import annotations

import math
import re
from enum import Enum
from typing import Any


class TaskComplexity(Enum):
    FAST = "fast"
    MEDIUM = "medium"
    HIGH = "high"
    VISION = "vision"


MODEL_TIER_MAP = {
    TaskComplexity.FAST: "gemini-3-flash",
    TaskComplexity.MEDIUM: "gemini-3.6-flash-high",
    TaskComplexity.HIGH: "gemini-3.1-pro-high",
    TaskComplexity.VISION: "gemini-3.1-flash-image",
}

RECOMMENDED_TOKEN_LIMITS = {
    TaskComplexity.FAST: 256,
    TaskComplexity.MEDIUM: 2048,
    TaskComplexity.HIGH: 8192,
    TaskComplexity.VISION: 4096,
}


# Syntactic and Structural Markers for Code Density
CODE_CONTROL_KEYWORDS = {
    "def", "class", "function", "return", "import", "export", "async", "await",
    "if", "else", "elif", "for", "while", "try", "except", "finally", "with",
    "const", "let", "var", "struct", "template", "public", "private", "protected",
    "lambda", "yield", "raise", "throw", "catch", "namespace", "typedef", "sizeof",
    "select", "insert", "update", "delete", "from", "where", "join", "group", "by"
}

CODE_SYNTAX_CHARS = set("{}[]();=+-*/<>:!&|%^~#@")

ANALYTICAL_DIRECTIVES = {
    "analyze", "refactor", "optimize", "debug", "architect", "benchmark",
    "compare", "derive", "proof", "evaluate", "implement", "redesign",
    "traceback", "exception", "algorithm", "complexity", "tradeoff",
    "quicksort", "theorem", "derivation", "formula", "latex", "matrix",
    "integral", "equation", "calculus", "asymptotic", "induction"
}


class ComplexityAnalyzer:
    """
    Multi-dimensional structural and statistical analyzer for LLM prompts.
    Computes a composite complexity score S in [0, 100].
    """

    @staticmethod
    def compute_code_density(text: str) -> float:
        """Analyzes syntax operator ratio, control structures, and code block density."""
        if not text:
            return 0.0

        score = 0.0

        # Fenced code block presence
        code_fence_count = len(re.findall(r"```", text))
        if code_fence_count >= 2:
            score += 40.0
        elif code_fence_count == 1:
            score += 20.0

        words = re.findall(r"\b[a-zA-Z_]\w*\b", text.lower())
        total_words = len(words) or 1

        # Control keyword density
        code_kw_matches = sum(1 for w in words if w in CODE_CONTROL_KEYWORDS)
        kw_ratio = code_kw_matches / total_words
        score += min(35.0, kw_ratio * 200.0)

        # Syntax character density
        syntax_char_count = sum(1 for char in text if char in CODE_SYNTAX_CHARS)
        char_ratio = syntax_char_count / max(1, len(text))
        score += min(25.0, char_ratio * 150.0)

        # Indentation & multiline structure depth
        lines = text.splitlines()
        indented_lines = sum(1 for line in lines if line.startswith("    ") or line.startswith("\t"))
        if len(lines) > 3 and indented_lines > 0:
            score += min(15.0, (indented_lines / len(lines)) * 30.0)

        return min(100.0, score)

    @staticmethod
    def compute_cognitive_depth(text: str) -> float:
        """Evaluates vocabulary sophistication, average word length, and analytical directives."""
        if not text:
            return 0.0

        words = re.findall(r"\b[a-zA-Z_]\w*\b", text.lower())
        if not words:
            return 0.0

        score = 0.0
        total_words = len(words)

        # Unique word ratio (lexical diversity)
        unique_ratio = len(set(words)) / total_words
        score += unique_ratio * 20.0

        # Average word length
        avg_len = sum(len(w) for w in words) / total_words
        score += min(20.0, max(0.0, (avg_len - 4.0) * 8.0))

        # Long technical words count (> 7 characters)
        long_words_count = sum(1 for w in words if len(w) > 7)
        long_ratio = long_words_count / total_words
        score += min(30.0, long_ratio * 120.0)

        # Analytical intent directives
        analytical_matches = sum(1 for w in words if w in ANALYTICAL_DIRECTIVES)
        score += min(30.0, analytical_matches * 10.0)

        return min(100.0, score)

    @staticmethod
    def compute_task_scope(text: str) -> float:
        """Detects multi-step directives, sub-task list structures, and constraint markers."""
        if not text:
            return 0.0

        score = 0.0

        # Bullet lists / numbered steps (e.g. 1., 2., -, *)
        list_items = len(re.findall(r"^\s*(\d+\.|[\-\*])\s+", text, re.MULTILINE))
        score += min(40.0, list_items * 10.0)

        # Sub-questions / instruction count
        question_count = text.count("?")
        score += min(20.0, question_count * 8.0)

        # Strict formatting & schema constraints
        if any(marker in text.lower() for marker in ["json", "xml", "schema", "format as", "output format"]):
            score += 20.0

        return min(100.0, score)

    @staticmethod
    def compute_length_score(char_count: int) -> float:
        """Non-linear scaling score for prompt length."""
        if char_count <= 20:
            return 0.0
        if char_count <= 60:
            return 10.0
        # Sigmoidal growth up to 100
        score = (100.0 / (1.0 + math.exp(-0.003 * (char_count - 500))))
        return min(100.0, max(10.0, score))

    @staticmethod
    def compute_history_score(messages: list[dict[str, Any]]) -> float:
        """Evaluates conversation turn depth and context accumulation."""
        if not messages:
            return 0.0
        turn_count = len(messages)
        return min(100.0, turn_count * 8.0)


def calculate_complexity_score(
    messages: list[dict[str, Any]] | None = None,
    system: str = "",
    task_type: str | None = None
) -> tuple[float, TaskComplexity, dict[str, float]]:
    """
    Calculates the multi-vector composite complexity score S in [0, 100] and maps to a TaskComplexity tier.
    Returns: (composite_score, complexity_tier, breakdown_dict)
    """
    # Explicit task type hint override
    if task_type:
        t = task_type.lower()
        if t in ("vision", "ocr", "screen", "image"):
            return 100.0, TaskComplexity.VISION, {"override": 100.0}
        if t in ("code", "coding", "architecture", "refactor", "debug", "math", "logic", "reasoning", "security"):
            return 75.0, TaskComplexity.HIGH, {"override": 75.0}
        if t in ("fast", "status", "quick", "lite", "ping"):
            return 5.0, TaskComplexity.FAST, {"override": 5.0}

    if not messages:
        return 25.0, TaskComplexity.MEDIUM, {"default": 25.0}

    combined_text = [system] if system else []
    has_image = False

    for msg in messages:
        content = msg.get("content")
        if content is None:
            continue

        if isinstance(content, str):
            combined_text.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") in ("image_url", "image", "inline_data") or "image_url" in part:
                        has_image = True
                    text_val = part.get("text", "")
                    if text_val:
                        combined_text.append(text_val)

    if has_image:
        return 100.0, TaskComplexity.VISION, {"vision_payload": 100.0}

    full_text = "\n".join(combined_text).strip()
    char_len = len(full_text)

    # Simple short greeting check (< 30 chars, single phrase)
    if char_len < 30 and full_text.lower().strip() in ("hi", "hello", "hey", "ping", "status", "ok", "thanks"):
        return 5.0, TaskComplexity.FAST, {"fast_greeting": 5.0}

    analyzer = ComplexityAnalyzer()
    s_code = analyzer.compute_code_density(full_text)
    s_cognitive = analyzer.compute_cognitive_depth(full_text)
    s_task = analyzer.compute_task_scope(full_text)
    s_length = analyzer.compute_length_score(char_len)
    s_history = analyzer.compute_history_score(messages)

    # Weighted composite score formula
    base_score = (
        0.40 * s_code +
        0.30 * s_cognitive +
        0.15 * s_task +
        0.10 * s_length +
        0.05 * s_history
    )

    # Boost score if significant code syntax or technical reasoning is present
    if s_code >= 30.0:
        composite_score = max(base_score, 25.0 + 0.6 * s_code)
    elif s_cognitive >= 70.0:
        composite_score = max(base_score, 20.0 + 0.45 * s_cognitive)
    else:
        composite_score = base_score

    breakdown = {
        "code_density": round(s_code, 2),
        "cognitive_depth": round(s_cognitive, 2),
        "task_scope": round(s_task, 2),
        "length_score": round(s_length, 2),
        "history_score": round(s_history, 2),
        "composite_score": round(composite_score, 2),
    }

    if composite_score < 15.0:
        tier = TaskComplexity.FAST
    elif composite_score < 50.0:
        tier = TaskComplexity.MEDIUM
    else:
        tier = TaskComplexity.HIGH

    return composite_score, tier, breakdown


def analyze_complexity(
    messages: list[dict[str, Any]] | None = None,
    system: str = "",
    task_type: str | None = None
) -> TaskComplexity:
    """Wrapper function returning TaskComplexity tier."""
    _, tier, _ = calculate_complexity_score(messages=messages, system=system, task_type=task_type)
    return tier


def select_model_for_prompt(
    messages: list[dict[str, Any]] | None = None,
    system: str = "",
    task_type: str | None = None,
    override_model: str | None = None
) -> str:
    """Selects optimal model ID using composite multi-dimensional complexity score."""
    if override_model and isinstance(override_model, str) and override_model.strip():
        return override_model.strip()

    try:
        from config.models import get_model_config
        cfg = get_model_config()
    except Exception:
        cfg = {}

    _, complexity, _ = calculate_complexity_score(messages=messages, system=system, task_type=task_type)
    default_target = MODEL_TIER_MAP[complexity]

    if complexity == TaskComplexity.HIGH:
        return cfg.get("gemini_code", cfg.get("gemini_reasoning", default_target))
    elif complexity == TaskComplexity.FAST:
        return cfg.get("gemini_fast", default_target)
    elif complexity == TaskComplexity.VISION:
        return cfg.get("gemini_vision", default_target)
    else:
        return cfg.get("gemini_general", default_target)


def get_recommended_token_limit(
    complexity: TaskComplexity,
    user_max_tokens: int | None = None
) -> int:
    """Returns recommended output token budget based on complexity tier."""
    if user_max_tokens and user_max_tokens > 0:
        return user_max_tokens
    return RECOMMENDED_TOKEN_LIMITS.get(complexity, 2048)


def estimate_tokens(text: str | Any) -> int:
    """Heuristic token estimator (~4 characters per token)."""
    if not text:
        return 0
    if not isinstance(text, str):
        text = str(text)
    return max(1, len(text) // 4)


def prune_messages_to_fit_budget(
    messages: list[dict[str, Any]],
    system: str = "",
    max_input_tokens: int = 16000
) -> list[dict[str, Any]]:
    """Adapts conversation history so total estimated input tokens fit within max_input_tokens budget."""
    if not messages:
        return []

    system_tokens = estimate_tokens(system)
    budget_for_messages = max(500, max_input_tokens - system_tokens)

    total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in messages)
    if total_tokens <= budget_for_messages:
        return messages

    pruned = list(messages)
    while len(pruned) > 1 and sum(estimate_tokens(m.get("content", "")) for m in pruned) > budget_for_messages:
        pruned.pop(0)

    return pruned
