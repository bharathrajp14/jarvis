# tests/test_context_engine.py — Unit Tests for Priority 3 Context Engine
from __future__ import annotations

import pytest
from context.builder import ContextBuilder
from context.compressor import ContextCompressor
from context.engine import ContextEngine, get_context_engine
from context.token_counter import TokenCounter
from context.types import AssembledContext, ContextItem, ContextScope, TokenBudget


def test_token_counter():
    text = "Hello world! This is a test string for token estimation."
    count = TokenCounter.count(text)
    assert count > 0
    assert isinstance(count, int)


def test_context_compressor():
    long_text = "\n\n  Line 1  \n\n  Line 2  \n\n" + ("Long detail line\n" * 50)
    cleaned = ContextCompressor.clean_text(long_text)
    assert "\n\n\n" not in cleaned

    compressed = ContextCompressor.compress(cleaned, max_tokens=30)
    assert TokenCounter.count(compressed) <= 100


def test_context_builder():
    budget = TokenBudget(max_tokens=1000, reserve_response_tokens=200)
    builder = ContextBuilder(budget=budget)

    item1 = ContextItem(scope=ContextScope.CONVERSATION, title="Chat", content="User asked for weather", priority=10)
    item2 = ContextItem(scope=ContextScope.SYSTEM_STATE, title="OS", content="CPU: 15.0%", priority=8)

    builder.add_item(item1).add_item(item2)
    assembled = builder.assemble()

    assert isinstance(assembled, AssembledContext)
    assert assembled.total_tokens > 0
    assert len(assembled.items) == 2
    assert "User asked for weather" in assembled.context_str


def test_context_engine_singleton():
    engine = get_context_engine()
    assert isinstance(engine, ContextEngine)

    assembled = engine.assemble_system_context(
        conversation_history=[{"role": "user", "content": "Hi"}],
        active_goal="Test Goal",
        max_tokens=4096
    )
    assert assembled.total_tokens > 0
    assert "Test Goal" in assembled.context_str


def test_context_engine_dynamic_profile_budget():
    engine = get_context_engine()
    
    # 1. Call context engine with gemini profile
    assembled_gemini = engine.assemble_system_context(profile="gemini")
    
    # 2. Call context engine with ollama profile
    assembled_ollama = engine.assemble_system_context(profile="ollama")
    
    # 3. Prove that they actually produce different budgets
    assert assembled_gemini.budget.max_tokens == 1000000
    assert assembled_ollama.budget.max_tokens == 32000
    assert assembled_gemini.budget.max_tokens != assembled_ollama.budget.max_tokens
