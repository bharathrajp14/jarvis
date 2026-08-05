# tests/test_executor_engine.py — Unit Tests for Priority 6 Parallel Execution Engine
from __future__ import annotations

import asyncio
import pytest
from agent.executor_engine import ParallelExecutionEngine, get_executor_engine
from agent.planner_engine import get_planner_engine
from agent.types import StepStatus


@pytest.mark.asyncio
async def test_executor_engine_execution():
    planner = get_planner_engine()
    executor = get_executor_engine()

    raw_steps = [
        {"step": 1, "tool": "open_app", "description": "Open Chrome", "parallel": True},
        {"step": 2, "tool": "open_app", "description": "Open Spotify", "parallel": True},
        {"step": 3, "tool": "web_search", "description": "Search news", "depends_on": [1]},
    ]
    graph = planner.create_goal_graph("Parallel startup", raw_steps)

    report = await executor.execute_graph(graph)
    assert report.status == "SUCCESS"
    assert report.completed_steps == 3
    assert report.duration_s > 0


@pytest.mark.asyncio
async def test_executor_human_interlock():
    planner = get_planner_engine()
    executor = ParallelExecutionEngine(max_workers=2)

    raw_steps = [
        {"step": 1, "tool": "file_controller", "description": "delete system files", "parameters": {"path": "C:\\"}},
    ]
    graph = planner.create_goal_graph("Destructive test", raw_steps)

    report = await executor.execute_graph(graph)
    assert graph.steps[0].status == StepStatus.WAITING_FOR_APPROVAL
    assert report.completed_steps == 0
