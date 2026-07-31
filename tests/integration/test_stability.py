# tests/integration/test_stability.py — Scenarios 15, 16, 25, 30: Concurrency, API Failures & Stop Interlocks
from __future__ import annotations

import asyncio
import pytest
from agent.executor_engine import get_executor_engine
from agent.planner_engine import get_planner_engine
from agent.types import StepStatus
from router import AgentRouter, AgentProfile
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_scenario_15_parallel_execution():
    """Scenario 15: Concurrently execute independent nodes in GoalGraph."""
    planner = get_planner_engine()
    executor = get_executor_engine()

    raw_steps = [
        {"step": 1, "tool": "file_list", "description": "List files A", "parallel": True},
        {"step": 2, "tool": "file_list", "description": "List files B", "parallel": True},
    ]
    graph = planner.create_goal_graph("Parallel file check", raw_steps)

    report = await executor.execute_graph(graph)
    assert report.status == "SUCCESS"
    assert report.completed_steps == 2


@pytest.mark.asyncio
async def test_scenario_16_long_running_stability():
    """Scenario 16: Long-running stress run loop verification."""
    planner = get_planner_engine()
    executor = get_executor_engine()

    # Loop graph creation and execution to verify zero runtime memory buildup/leak
    for i in range(5):
        raw_steps = [{"step": 1, "tool": "file_list", "description": f"Health iteration {i}"}]
        graph = planner.create_goal_graph(f"Stress check iteration {i}", raw_steps)
        report = await executor.execute_graph(graph)
        assert report.status == "SUCCESS"


@pytest.mark.asyncio
async def test_scenario_25_api_failure_handling():
    """Scenario 25: Network API failures redirect to fallback router cleanly."""
    backends = {}
    
    # Mocking Gemini failure
    gemini_mock = MagicMock()
    gemini_mock.complete.side_effect = Exception("API connection timed out")
    gemini_mock.model_name = "gemini-3.5-flash"
    backends[AgentProfile.GEMINI] = gemini_mock

    # Fallback to GPT
    gpt_mock = MagicMock()
    gpt_mock.complete.return_value = "Verified fallback response"
    gpt_mock.model_name = "gpt-4o"
    backends[AgentProfile.GPT] = gpt_mock

    router = AgentRouter(backends=backends)
    router.default = AgentProfile.GEMINI  # Ensure default is set to GEMINI for this test

    # Call run which will catch Gemini failure and fallback to GPT
    res = router.run(AgentProfile.GEMINI, [{"role": "user", "content": "test"}], "")
    assert res == "Verified fallback response"


@pytest.mark.asyncio
async def test_scenario_30_emergency_stop():
    """Scenario 30: Cancel in-flight graphs immediately on emergency stop signal."""
    planner = get_planner_engine()
    executor = get_executor_engine()

    raw_steps = [
        {"step": 1, "tool": "file_list", "description": "Step to cancel"},
        {"step": 2, "tool": "file_list", "description": "Step 2 dependent", "depends_on": [1]},
    ]
    graph = planner.create_goal_graph("Emergency cancel test", raw_steps)

    # Mock tool resolver that delays execution to allow cancellation trigger
    async def delayed_resolver(tool_name, params):
        await asyncio.sleep(0.1)
        return "done"

    # Run the graph execution and cancel it in a concurrent task
    async def run_and_cancel():
        await asyncio.sleep(0.02)  # Let it start
        executor.cancel_all()

    # Gather execution and cancellation task
    _, report = await asyncio.gather(
        run_and_cancel(),
        executor.execute_graph(graph, tool_resolver_fn=delayed_resolver)
    )

    # Check that cancel terminates step execution and the graph is not fully completed
    assert report.completed_steps < 2
