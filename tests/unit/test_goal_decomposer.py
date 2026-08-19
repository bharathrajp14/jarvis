"""
Tests for GoalDecomposer — MK40.2 §7

Verifies:
  - decompose_goal returns a GoalSpec with non-empty required_operations
  - Portfolio + GitHub push goal correctly identifies CREATE_PORTFOLIO and PUSH_TO_GITHUB
  - Unrelated goal cannot produce portfolio criteria
  - Empty/None goal produces a safe fallback
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_portfolio_github_goal_decomposition():
    """Portfolio creation + GitHub push goal must decompose to both operations."""
    from brjarvis.agent.goal_decomposer import _decompose_deterministic

    # Use deterministic to avoid LLM dependency in unit tests
    spec = _decompose_deterministic("Create a portfolio and push it to GitHub, then open it.")

    assert "CREATE_PORTFOLIO" in spec.required_operations
    assert "PUSH_TO_GITHUB" in spec.required_operations
    assert "OPEN_PORTFOLIO" in spec.required_operations
    assert spec.decomposed_by == "deterministic"


@pytest.mark.unit
def test_unrelated_goal_does_not_produce_portfolio_criteria():
    """A web search goal must not produce CREATE_PORTFOLIO criteria."""
    from brjarvis.agent.goal_decomposer import _decompose_deterministic

    spec = _decompose_deterministic("Search for the latest AI news and give me a summary.")

    assert "CREATE_PORTFOLIO" not in spec.required_operations
    assert "WEB_SEARCH" in spec.required_operations


@pytest.mark.unit
def test_empty_goal_returns_safe_fallback():
    """Empty goal must return a safe GoalSpec with EXECUTE_GOAL fallback."""
    from brjarvis.agent.goal_decomposer import decompose_goal

    spec = decompose_goal("")

    assert spec is not None
    assert spec.required_operations == ["EXECUTE_GOAL"]
    assert spec.original_request == ""


@pytest.mark.unit
def test_git_commit_goal_decomposition():
    """Git commit goal must include GIT_COMMIT operation."""
    from brjarvis.agent.goal_decomposer import _decompose_deterministic

    spec = _decompose_deterministic("Stage all changes and commit to the repo.")

    assert "GIT_COMMIT" in spec.required_operations


@pytest.mark.unit
def test_goal_spec_serialization_roundtrip():
    """GoalSpec must survive to_dict() → from_dict() roundtrip."""
    from brjarvis.agent.goal_decomposer import GoalSpec, _decompose_deterministic

    spec = _decompose_deterministic("Create a portfolio and push to GitHub.")
    d = spec.to_dict()
    restored = GoalSpec.from_dict(d)

    assert restored.required_operations == spec.required_operations
    assert restored.original_request == spec.original_request
    assert len(restored.acceptance_criteria) == len(spec.acceptance_criteria)


@pytest.mark.unit
def test_goal_spec_original_request_preserved():
    """original_request must be stored verbatim — not modified."""
    from brjarvis.agent.goal_decomposer import _decompose_deterministic

    goal = "Create portfolio and push it to GitHub, then open it."
    spec = _decompose_deterministic(goal)

    assert spec.original_request == goal
