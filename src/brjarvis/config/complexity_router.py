# src/brjarvis/config/complexity_router.py — Multi-Dimensional AI Semantic Complexity Analyzer
"""
AI-Driven Semantic & Information-Theoretic Complexity Analyzer for BR JARVIS.
Calculates a weighted complexity score S in [0, 100] based on 5 structural & statistical vectors:
  1. Shannon Information Entropy & Lexical Diversity (measures reasoning depth & vocabulary density)
  2. Structural & AST Syntactic Density (measures code/logic/markup complexity without keyword whitelists)
  3. Imperative & Multi-Clause Task Scope (measures multi-step instruction depth and constraint rules)
  4. Non-linear Context & Payload Scale
  5. Multimodal Payload Detection
"""
from __future__ import annotations

import math
import os
import re
from enum import Enum
from typing import Any


class TaskComplexity(Enum):
    FAST = "fast"
    MEDIUM = "medium"
    HIGH = "high"
    VISION = "vision"


MODEL_TIER_MAP = {
    TaskComplexity.FAST: "gemini-3.6-flash-medium",
    TaskComplexity.MEDIUM: "gemini-3.7-flash-high",
    TaskComplexity.HIGH: "gemini-3.1-pro-high",
    TaskComplexity.VISION: "gemini-3.1-flash-image",
}


class DynamicTokenBudgetMap(dict):
    """Auto-flexible token budget map.
    
    Dynamically scales output token limits using semantic context payload analysis,
    information entropy, and complexity score rather than hardcoded string lookups.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sync_env_overrides()

    def _sync_env_overrides(self) -> None:
        """Sync overrides from environment or models.json config."""
        try:
            from brjarvis.config.models import get_model_config
            cfg = get_model_config()
        except Exception:
            cfg = {}

        env_fast = os.environ.get("JARVIS_TOKEN_LIMIT_FAST") or cfg.get("token_limit_fast")
        env_medium = os.environ.get("JARVIS_TOKEN_LIMIT_MEDIUM") or cfg.get("token_limit_medium")
        env_high = os.environ.get("JARVIS_TOKEN_LIMIT_HIGH") or cfg.get("token_limit_high")
        env_vision = os.environ.get("JARVIS_TOKEN_LIMIT_VISION") or cfg.get("token_limit_vision")

        if env_fast and str(env_fast).isdigit():
            self[TaskComplexity.FAST] = int(env_fast)
        if env_medium and str(env_medium).isdigit():
            self[TaskComplexity.MEDIUM] = int(env_medium)
        if env_high and str(env_high).isdigit():
            self[TaskComplexity.HIGH] = int(env_high)
        if env_vision and str(env_vision).isdigit():
            self[TaskComplexity.VISION] = int(env_vision)

    def get_flexible_limit(
        self,
        complexity: TaskComplexity,
        user_max_tokens: int | None = None,
        messages: list[dict[str, Any]] | None = None,
        system: str = "",
        score: float | None = None,
    ) -> int:
        """Calculate an AI-driven adaptive output token limit."""
        if user_max_tokens and isinstance(user_max_tokens, int) and user_max_tokens > 0:
            return user_max_tokens

        self._sync_env_overrides()
        base_limit = self.get(complexity, 4096)

        # Dynamic AI semantic payload evaluation
        full_text = system or ""
        if messages:
            for m in messages:
                c = m.get("content", "")
                if isinstance(c, str):
                    full_text += " " + c

        # 1. Structural entropy & length metric
        char_len = len(full_text)
        entropy = ComplexityAnalyzer.compute_shannon_entropy(full_text)
        
        # 2. Structural punctuation & code fence density
        syntax_ratio = ComplexityAnalyzer.compute_structural_density(full_text) / 100.0

        # Multiplier derived from information entropy and structural density (AI dynamic scaling)
        multiplier = 1.0 + (entropy / 8.0) * 0.4 + syntax_ratio * 0.8
        if score and isinstance(score, (int, float)):
            multiplier += (score / 100.0) * 0.5
        elif char_len > 300:
            multiplier += min(1.0, (char_len / 2000.0))

        calculated = int(base_limit * multiplier)
        
        # Hard cap floor/ceiling based on model context limits
        max_cap = int(os.environ.get("JARVIS_TOKEN_LIMIT_MAX", "32768"))
        return max(base_limit, min(calculated, max_cap))


RECOMMENDED_TOKEN_LIMITS = DynamicTokenBudgetMap({
    TaskComplexity.FAST: 1024,
    TaskComplexity.MEDIUM: 4096,
    TaskComplexity.HIGH: 16384,
    TaskComplexity.VISION: 8192,
})


# Pure AST & Syntactic Operators (universal across code, markup, math, JSON)
CODE_SYNTAX_CHARS = set("{}[]();=+-*/<>:!&|%^~#@")


class ComplexityAnalyzer:
    """
    Multi-dimensional AI structural and statistical information-theoretic analyzer.
    Computes a composite complexity score S in [0, 100] without relying on hardcoded keyword lists.
    """

    @staticmethod
    def compute_shannon_entropy(text: str) -> float:
        """Calculates Shannon Information Entropy H(X) in bits per character."""
        if not text:
            return 0.0
        frequencies = {}
        for char in text:
            frequencies[char] = frequencies.get(char, 0) + 1
        entropy = 0.0
        text_len = len(text)
        for count in frequencies.values():
            p = count / text_len
            entropy -= p * math.log2(p)
        return round(entropy, 4)

    @staticmethod
    def compute_structural_density(text: str) -> float:
        """Analyzes syntax operator ratios, code block fencing, indentation, and AST symbols."""
        if not text:
            return 0.0

        score = 0.0

        # Fenced code block presence (e.g. ``` python ... ```)
        code_fence_count = len(re.findall(r"```", text))
        if code_fence_count >= 2:
            score += 40.0
        elif code_fence_count == 1:
            score += 20.0

        # Syntax operator and AST symbol density (universal language indicators)
        syntax_char_count = sum(1 for char in text if char in CODE_SYNTAX_CHARS)
        char_ratio = syntax_char_count / max(1, len(text))
        score += min(45.0, char_ratio * 250.0)

        # AST structure indicators (parentheses, colons, brackets, assignments)
        if re.search(r"\(.*?\)|\[.*?\]|\{.*?\}|:\s*$", text, re.MULTILINE):
            score += 15.0

        # Indentation & multiline structure depth
        lines = text.splitlines()
        if len(lines) > 2:
            indented_lines = sum(1 for line in lines if line.startswith("    ") or line.startswith("\t"))
            if indented_lines > 0:
                score += min(30.0, (indented_lines / len(lines)) * 50.0)

        return min(100.0, score)

    @staticmethod
    def compute_cognitive_depth(text: str) -> float:
        """Evaluates Shannon information entropy, lexical diversity, and word complexity."""
        if not text:
            return 0.0

        words = re.findall(r"\b[a-zA-Z_]\w*\b", text.lower())
        if not words:
            return 0.0

        score = 0.0
        total_words = len(words)

        # 1. Lexical Diversity (Unique word ratio)
        unique_ratio = len(set(words)) / total_words
        score += unique_ratio * 25.0

        # 2. Average word length & multi-syllable word ratio (> 7 chars)
        avg_len = sum(len(w) for w in words) / total_words
        score += min(25.0, max(0.0, (avg_len - 4.0) * 10.0))

        # 3. Information Entropy Scaling
        entropy = ComplexityAnalyzer.compute_shannon_entropy(text)
        score += min(30.0, max(0.0, (entropy - 3.5) * 15.0))

        # 4. Long analytical word ratio (> 8 chars)
        long_words = sum(1 for w in words if len(w) > 8)
        score += min(20.0, (long_words / total_words) * 100.0)

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

        # Multi-sentence clause complexity
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if len(sentences) > 2:
            score += min(20.0, len(sentences) * 4.0)

        # Strict formatting & structural constraints (brackets, colons, schema markers)
        if any(marker in text for marker in ["{", "}", "[", "]", ":"]):
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
    norm_text = full_text.lower().strip()
    if char_len < 30 and norm_text in ("hi", "hello", "hey", "ping", "status", "ok", "thanks"):
        return 5.0, TaskComplexity.FAST, {"fast_greeting": 5.0}

    s_code = ComplexityAnalyzer.compute_structural_density(full_text)
    s_cognitive = ComplexityAnalyzer.compute_cognitive_depth(full_text)
    s_task = ComplexityAnalyzer.compute_task_scope(full_text)
    s_length = ComplexityAnalyzer.compute_length_score(char_len)
    s_history = ComplexityAnalyzer.compute_history_score(messages)

    # Weighted composite score formula
    base_score = (
        0.40 * s_code +
        0.30 * s_cognitive +
        0.15 * s_task +
        0.10 * s_length +
        0.05 * s_history
    )

    # Boost score if significant syntax structure or information density is present
    if s_code >= 30.0:
        composite_score = max(base_score, 28.0 + 0.62 * s_code)
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
        from brjarvis.config.models import get_model_config
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
    user_max_tokens: int | None = None,
    messages: list[dict[str, Any]] | None = None,
    system: str = "",
    score: float | None = None,
) -> int:
    """Returns AI-driven auto-flexible dynamic output token budget based on complexity tier and context."""
    return RECOMMENDED_TOKEN_LIMITS.get_flexible_limit(
        complexity,
        user_max_tokens=user_max_tokens,
        messages=messages,
        system=system,
        score=score,
    )


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

    pruned = []
    accumulated_tokens = 0
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg.get("content", ""))
        if accumulated_tokens + msg_tokens <= budget_for_messages:
            pruned.insert(0, msg)
            accumulated_tokens += msg_tokens
        else:
            break

    if not pruned and messages:
        pruned = [messages[-1]]

    return pruned
