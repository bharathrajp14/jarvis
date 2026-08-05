# tests/test_mk38_phase1_upgrades.py — Unit & Integration Tests for MK38 Phase 8.1 Upgrades
import pytest
import tempfile
from pathlib import Path

from reasoning.meta_cognition import MetaCognitionEngine, get_meta_cognition
from reasoning.speculative import SpeculativeExecutionEngine, SpeculativeDraftStep
from memory.experience_replay import ExperienceReplayStore, ExperienceTrajectory


def test_meta_cognition_eval():
    engine = MetaCognitionEngine(confidence_threshold=0.70)
    
    # 1. Normal query assessment
    res = engine.evaluate_intent("Check system CPU telemetry and RAM usage")
    assert res.confidence_score >= 0.70
    assert res.suggested_action == "PROCEED"

    # 2. High-risk operation assessment
    res_risk = engine.evaluate_intent("Delete all database files and format drive")
    assert res_risk.perceived_risk == "HIGH"
    assert res_risk.suggested_action in ("CLARIFY", "RE-PLAN")


def test_speculative_execution():
    spec = SpeculativeExecutionEngine()
    
    # Generate draft step for file viewing
    draft = spec.generate_draft_step("Read contents of file /path/to/script.py", 1, [])
    assert draft is not None
    assert draft.tool_name == "view_file"
    assert draft.tool_args["AbsolutePath"] == "/path/to/script.py"

    # Test validation & metrics
    is_valid = spec.validate_and_merge(draft, "view_file", {"AbsolutePath": "/path/to/script.py"})
    assert is_valid is True
    
    metrics = spec.get_metrics()
    assert metrics["accepted_count"] == 1
    assert metrics["acceptance_rate_percent"] == 100.0


def test_experience_replay_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ExperienceReplayStore(db_dir=Path(tmpdir))
        
        # Record trajectory
        traj = ExperienceTrajectory(
            goal_query="Refactor router.py to use multi-objective scoring",
            success_status=True,
            step_count=3,
            tool_sequence=["view_file", "replace_file_content", "run_command"],
        )
        store.record_trajectory(traj)

        # Record failed trajectory
        failed_traj = ExperienceTrajectory(
            goal_query="Deploy broken python script to production",
            success_status=False,
            step_count=2,
            tool_sequence=["run_command"],
            failure_reason="SyntaxError in script",
        )
        store.record_trajectory(failed_traj)

        # Retrieve successful patterns
        succ = store.get_successful_patterns("router.py")
        assert len(succ) == 1
        assert succ[0]["goal_query"] == traj.goal_query

        # Retrieve failed patterns
        fails = store.get_similar_failures("script")
        assert len(fails) == 1
        assert fails[0]["failure_reason"] == "SyntaxError in script"

        store.close()
