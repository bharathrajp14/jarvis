# tests/unit/test_experience_learning.py — Experience Replay & Trajectory Learning Tests
from __future__ import annotations

from memory.experience_replay import ExperienceReplayStore, ExperienceTrajectory
from memory.unified_memory import get_unified_memory


def test_record_and_retrieve_experience_trajectories(tmp_path):
    store = ExperienceReplayStore(db_dir=tmp_path)

    # 1. Record successful trajectory
    t_success = ExperienceTrajectory(
        goal_query="Open Chrome and navigate to python docs",
        success_status=True,
        step_count=2,
        tool_sequence=["open_app", "web_search"],
    )
    store.record_trajectory(t_success)

    # 2. Record failed trajectory
    t_fail = ExperienceTrajectory(
        goal_query="Open Chrome and run broken code",
        success_status=False,
        step_count=1,
        tool_sequence=["run_code"],
        failure_reason="SyntaxError: invalid syntax",
    )
    store.record_trajectory(t_fail)

    # 3. Retrieve patterns
    successes = store.get_successful_patterns("Chrome python", limit=5)
    assert len(successes) == 1
    assert successes[0]["goal_query"] == "Open Chrome and navigate to python docs"
    assert successes[0]["tool_sequence"] == ["open_app", "web_search"]

    failures = store.get_similar_failures("Chrome broken code", limit=5)
    assert len(failures) == 1
    assert failures[0]["failure_reason"] == "SyntaxError: invalid syntax"

    store.close()


def test_unified_memory_experience_integration(tmp_path):
    um = get_unified_memory()
    um.record_execution_experience(
        goal="Check system disk space",
        success=True,
        tool_sequence=["system_health"],
    )

    exp = um.get_relevant_experiences("disk space", limit=3)
    assert "successes" in exp
    assert "failures" in exp
