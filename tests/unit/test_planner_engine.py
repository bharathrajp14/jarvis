# tests/test_planner_engine.py — Unit Tests for Priority 5 Autonomous Planner Engine
from __future__ import annotations

import pytest
from agent.planner_engine import PlannerEngine, get_planner_engine
from agent.types import GoalGraph, RiskLevel, StepStatus, TaskStepNode


def test_planner_engine_risk_assessment():
    planner = get_planner_engine()

    raw_steps = [
        {"step": 1, "tool": "web_search", "description": "Search AI trends", "parameters": {"query": "AI"}},
        {"step": 2, "tool": "file_controller", "description": "delete temporary build folder", "parameters": {"path": "tmp"}},
    ]

    graph = planner.create_goal_graph("Clean temporary files", raw_steps)

    assert isinstance(graph, GoalGraph)
    assert len(graph.steps) == 2
    assert graph.steps[0].risk_level == RiskLevel.LOW
    assert graph.steps[0].requires_approval is False

    assert graph.steps[1].risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert graph.steps[1].requires_approval is True
    assert graph.requires_user_confirmation is True


def test_planner_replanning():
    planner = get_planner_engine()
    raw_steps = [
        {"step": 1, "tool": "web_search", "description": "Search info"},
        {"step": 2, "tool": "code_helper", "description": "Write code"},
    ]
    graph = planner.create_goal_graph("Build software", raw_steps)
    graph.steps[0].status = StepStatus.SUCCESS

    replanned = planner.replan_failed_step(graph, failed_step_id=2, error="Syntax error in output")
    assert replanned.steps[0].status == StepStatus.SUCCESS
    assert replanned.steps[1].status == StepStatus.PENDING
    assert "_retry_fallback" in replanned.steps[1].parameters
