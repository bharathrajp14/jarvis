"""Unit tests for Model Configuration & Semantic Complexity Routing."""

from __future__ import annotations

import pytest

from brjarvis.config.complexity_router import (
    ComplexityAnalyzer,
    TaskComplexity,
    calculate_complexity_score,
    get_recommended_token_limit,
)
from brjarvis.config.models import get_model_config, get_model_for_task


@pytest.mark.unit
def test_model_config_defaults():
    """Verify default model configuration loads properly."""
    cfg = get_model_config()
    assert "default_backend" in cfg
    assert "gemini" in cfg
    assert "claude" in cfg
    assert "gpt" in cfg


@pytest.mark.unit
def test_get_model_for_task_routing():
    """Verify task types route to expected calibrated models."""
    code_model = get_model_for_task("code")
    assert "claude" in code_model or "pro" in code_model or "gemini" in code_model

    reasoning_model = get_model_for_task("reasoning")
    assert (
        "opus" in reasoning_model
        or "pro" in reasoning_model
        or "gemini" in reasoning_model
        or "claude" in reasoning_model
        or "thinking" in reasoning_model
    )

    vision_model = get_model_for_task("vision")
    assert "image" in vision_model or "flash" in vision_model

    fast_model = get_model_for_task("fast")
    assert "tiered" in fast_model or "lite" in fast_model or "flash" in fast_model


@pytest.mark.unit
def test_complexity_router_entropy_analysis():
    """Verify semantic complexity router calculates Shannon entropy and token budget."""
    simple_query = "What is the capital of France?"
    complex_query = """
    Architect an asynchronous event-driven distributed system in Python using FastAPI,
    SQLite WAL single-writer thread pool locks, and ChromaDB embeddings.
    Implement failure injection recovery and Shannon entropy complexity routing with AST validation.
    ```python
    def complex_pipeline():
        pass
    ```
    """

    simple_entropy = ComplexityAnalyzer.compute_shannon_entropy(simple_query)
    complex_entropy = ComplexityAnalyzer.compute_shannon_entropy(complex_query)
    assert complex_entropy > simple_entropy

    simple_score, simple_tier, _ = calculate_complexity_score([{"role": "user", "content": simple_query}])
    complex_score, complex_tier, _ = calculate_complexity_score([{"role": "user", "content": complex_query}])

    assert complex_score > simple_score
    assert complex_tier in (TaskComplexity.HIGH, TaskComplexity.MEDIUM)

    simple_budget = get_recommended_token_limit(simple_tier)
    complex_budget = get_recommended_token_limit(complex_tier)
    assert complex_budget >= simple_budget
