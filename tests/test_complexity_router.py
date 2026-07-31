import pytest
from config.complexity_router import (
    TaskComplexity,
    analyze_complexity,
    calculate_complexity_score,
    select_model_for_prompt,
    get_recommended_token_limit,
    estimate_tokens,
    prune_messages_to_fit_budget,
)


def test_fast_complexity():
    messages = [{"role": "user", "content": "hi"}]
    score, tier, breakdown = calculate_complexity_score(messages)
    assert tier == TaskComplexity.FAST
    assert score < 15.0
    assert select_model_for_prompt(messages) == "gemini-3-flash"
    assert get_recommended_token_limit(TaskComplexity.FAST) == 256

    messages_status = [{"role": "user", "content": "status"}]
    assert analyze_complexity(messages_status) == TaskComplexity.FAST


def test_medium_complexity():
    messages = [{"role": "user", "content": "Can you summarize the main features of our Python assistant application for the user report?"}]
    score, tier, breakdown = calculate_complexity_score(messages)
    assert tier == TaskComplexity.MEDIUM
    assert 15.0 <= score < 50.0
    assert select_model_for_prompt(messages) == "gemini-3.6-flash-high"
    assert get_recommended_token_limit(TaskComplexity.MEDIUM) == 2048


def test_high_complexity_code():
    messages = [{"role": "user", "content": "Write a python function to refactor a binary tree traversal algorithm with error handling:\ndef traverse(node):\n    if not node:\n        return\n    return traverse(node.left) + [node.val] + traverse(node.right)"}]
    score, tier, breakdown = calculate_complexity_score(messages)
    assert tier == TaskComplexity.HIGH
    assert score >= 50.0
    assert breakdown["code_density"] > 0
    assert select_model_for_prompt(messages) == "gemini-3.1-pro-high"
    assert get_recommended_token_limit(TaskComplexity.HIGH) == 8192


def test_high_complexity_long_prompt():
    long_text = "Analysis required for system architecture refactoring: " + ("def test_func(): return x * y + z\n" * 20)
    messages = [{"role": "user", "content": long_text}]
    score, tier, breakdown = calculate_complexity_score(messages)
    assert tier == TaskComplexity.HIGH
    assert score >= 50.0
    assert select_model_for_prompt(messages) == "gemini-3.1-pro-high"


def test_vision_complexity():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is in this image?"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}
            ]
        }
    ]
    score, tier, breakdown = calculate_complexity_score(messages)
    assert tier == TaskComplexity.VISION
    assert select_model_for_prompt(messages) in ("gemini-3.1-flash-image", "gemini-3.6-flash", "gemini-3-flash")
    assert get_recommended_token_limit(TaskComplexity.VISION) == 4096


def test_manual_model_override():
    messages = [{"role": "user", "content": "hi"}]
    assert select_model_for_prompt(messages, override_model="claude-opus-4-6") == "claude-opus-4-6"
    assert get_recommended_token_limit(TaskComplexity.FAST, user_max_tokens=500) == 500


def test_token_estimation_and_pruning():
    text = "hello world"
    assert estimate_tokens(text) == 2

    # Test pruning long history
    messages = [
        {"role": "user", "content": "message 1: " + ("x" * 2000)},
        {"role": "assistant", "content": "reply 1: " + ("y" * 2000)},
        {"role": "user", "content": "latest message: " + ("z" * 100)},
    ]
    # Restrict budget to fit only ~500 tokens
    pruned = prune_messages_to_fit_budget(messages, max_input_tokens=600)
    assert len(pruned) < len(messages)
    assert pruned[-1]["content"].startswith("latest message:")
