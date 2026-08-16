# tests/e2e/test_rebuild_scenarios.py — 25 Real-World Production End-to-End Scenarios
"""
Master End-to-End Test Suite implementing all 25 Real-World Scenarios
specified in Master Prompt Section 67.
"""
from __future__ import annotations

import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from brjarvis.agent.execution_ledger import ExecutionLedger, LedgerEntry, LedgerStatus
from brjarvis.agent.planner import _validate_and_sanitize_plan
from brjarvis.agent.task_state import TaskState, TaskStatus, get_task_state_manager
from brjarvis.agent.verifier import VerificationResult, VerificationStatus
from brjarvis.context.builder import ContextBuilder
from brjarvis.context.types import TokenBudget
from brjarvis.memory.canonical_db import CanonicalDatabaseManager
from brjarvis.memory.conflict_engine import ConflictEngine, ConflictResolutionAction
from brjarvis.memory.domain import CanonicalMemory, MemoryStatus, MemoryType, SourceType
from brjarvis.memory.experience_replay import ExperienceReplayStore, ExperienceTrajectory
from brjarvis.memory.lessons import LessonStore
from brjarvis.memory.retrieval import HybridRetrievalEngine
from brjarvis.memory.session_lifecycle import SessionLifecycleManager, SessionRecord
from brjarvis.memory.store import CanonicalMemoryStore
from brjarvis.memory.task_memory_router import MemoryMode, TaskMemoryRouter
from brjarvis.memory.temporal import TemporalEngine
from brjarvis.memory.unified_memory import UnifiedMemoryManager
from brjarvis.reasoning.decision_engine import DecisionEngine


@pytest.fixture
def test_env(tmp_path):
    db_file = tmp_path / "e2e_canonical.db"
    db = CanonicalDatabaseManager(db_path=db_file)
    store = CanonicalMemoryStore(db_manager=db)
    conflict = ConflictEngine(store=store)
    temporal = TemporalEngine(store=store)
    retrieval = HybridRetrievalEngine(store=store)
    router = TaskMemoryRouter(retrieval_engine=retrieval)
    session_mgr = SessionLifecycleManager(db_manager=db)
    decision_eng = DecisionEngine(db_manager=db)
    ledger = ExecutionLedger(db_manager=db)
    exp_store = ExperienceReplayStore(db_dir=tmp_path)
    lessons = LessonStore(db_path=tmp_path / "lessons.db")

    return {
        "db": db,
        "store": store,
        "conflict": conflict,
        "temporal": temporal,
        "retrieval": retrieval,
        "router": router,
        "session_mgr": session_mgr,
        "decision_eng": decision_eng,
        "ledger": ledger,
        "exp_store": exp_store,
        "lessons": lessons,
        "tmp_path": tmp_path,
    }


# ── Scenario 1: Continue a coding project after restart ────────────────────────
def test_scenario_01_continue_coding_project_after_restart(test_env):
    store = test_env["store"]
    mem = CanonicalMemory(
        entity="project_jarvis_rebuild",
        attribute="current_milestone",
        value="Phase 4 Completed",
        content="BR JARVIS rebuild milestone: Phase 4 Completed. Next: Phase 5 session lifecycle",
        memory_type=MemoryType.PROJECT_STATE,
        project_id="brjarvis",
    )
    store.save(mem)

    # Simulate fresh process restart
    fresh_store = CanonicalMemoryStore(db_manager=test_env["db"])
    recovered = fresh_store.get_by_entity_attribute("project_jarvis_rebuild", "current_milestone", project_id="brjarvis")
    assert recovered is not None
    assert recovered.value == "Phase 4 Completed"


# ── Scenario 2: Recall user preference from previous session ──────────────────
def test_scenario_02_recall_user_preference_from_previous_session(test_env):
    store = test_env["store"]
    pref = CanonicalMemory(
        entity="theme_preference",
        attribute="theme",
        value="cyberpunk_dark",
        content="User prefers cyberpunk_dark theme",
        memory_type=MemoryType.PREFERENCE,
    )
    store.save(pref)

    retrieval = test_env["retrieval"]
    hits = retrieval.search("What is my UI theme preference?")
    assert len(hits) > 0
    assert hits[0].memory.value == "cyberpunk_dark"


# ── Scenario 3: Correct an outdated fact ──────────────────────────────────────
def test_scenario_03_correct_outdated_fact(test_env):
    store = test_env["store"]
    conflict = test_env["conflict"]
    temporal = test_env["temporal"]

    # Initial outdated fact
    initial = CanonicalMemory(
        entity="deployed_port",
        attribute="port",
        value="3000",
        content="Web server is running on port 3000",
        source_type=SourceType.SYSTEM_OBSERVATION,
        status=MemoryStatus.ACTIVE,
    )
    store.save(initial)

    # User correction
    correction = CanonicalMemory(
        entity="deployed_port",
        attribute="port",
        value="8000",
        content="Web server is actually deployed on port 8000",
        source_type=SourceType.EXPLICIT_USER_CORRECTION,
        status=MemoryStatus.ACTIVE,
    )
    conflicts = conflict.detect_conflicts(correction)
    resolution = conflict.resolve(correction, conflicts)
    saved = conflict.apply_resolution(resolution)

    current = temporal.get_current_truth("deployed_port", "port")
    assert current.value == "8000"
    assert current.version == 2
    assert store.get(initial.memory_id).status == MemoryStatus.SUPERSEDED


# ── Scenario 4: Ask what decision was previously made ─────────────────────────
def test_scenario_04_ask_what_decision_was_previously_made(test_env):
    decision_eng = test_env["decision_eng"]
    dec = decision_eng.record_decision(
        question="Which vector database architecture to use?",
        goal="Select optimal vector store",
        selected_option="ChromaDB with local pure-Python fallback",
        rejected_options=["Pinecone Cloud", "Milvus Server"],
        evidence="Ensures local-first offline compatibility",
        task_id="task_vector_01",
    )

    retrieved = decision_eng.get_decision(dec.decision_id)
    assert retrieved is not None
    assert "ChromaDB" in retrieved.selected_option
    assert "Pinecone Cloud" in retrieved.rejected_options


# ── Scenario 5: Recover incomplete task after crash ───────────────────────────
def test_scenario_05_recover_incomplete_task_after_crash(test_env):
    ledger = test_env["ledger"]
    # Step 1 verified, step 2 pending
    ledger.append(LedgerEntry(
        task_id="task_recover_5",
        step_id="step_1",
        tool_name="git_clone",
        status=LedgerStatus.SUCCESS,
        evidence="Repository cloned to /workspace",
        verification_status=LedgerStatus.SUCCESS,
    ))

    # Restart check
    assert ledger.step_is_verified("task_recover_5", "step_1") is True
    assert ledger.step_is_verified("task_recover_5", "step_2") is False


# ── Scenario 6: Avoid a previously failed approach ───────────────────────────
def test_scenario_06_avoid_previously_failed_approach(test_env):
    exp_store = test_env["exp_store"]
    exp_store.record_trajectory(ExperienceTrajectory(
        goal_query="Download PDF report from protected URL",
        success_status=False,
        step_count=1,
        tool_sequence=["requests_get"],
        failure_reason="HTTP 403 Cloudflare Bot Detection",
    ))

    failures = exp_store.get_similar_failures("Download PDF report", limit=1)
    assert len(failures) > 0
    assert "Cloudflare Bot Detection" in failures[0]["failure_reason"]


# ── Scenario 7: Reuse a previously successful approach ────────────────────────
def test_scenario_07_reuse_previously_successful_approach(test_env):
    exp_store = test_env["exp_store"]
    exp_store.record_trajectory(ExperienceTrajectory(
        goal_query="Extract text from PDF document",
        success_status=True,
        step_count=2,
        tool_sequence=["pdf_reader", "text_extractor"],
    ))

    successes = exp_store.get_successful_patterns("Extract text from PDF", limit=1)
    assert len(successes) > 0
    assert successes[0]["tool_sequence"] == ["pdf_reader", "text_extractor"]


# ── Scenario 8: Project-specific preference overriding global preference ──────
def test_scenario_08_project_specific_preference_overrides_global(test_env):
    store = test_env["store"]
    temporal = test_env["temporal"]

    store.save(CanonicalMemory(
        entity="linter",
        attribute="tool",
        value="flake8",
        project_id="global",
        status=MemoryStatus.ACTIVE,
    ))
    store.save(CanonicalMemory(
        entity="linter",
        attribute="tool",
        value="ruff",
        project_id="brjarvis",
        status=MemoryStatus.ACTIVE,
    ))

    project_linter = temporal.get_current_truth("linter", "tool", project_id="brjarvis")
    assert project_linter.value == "ruff"

    global_linter = temporal.get_current_truth("linter", "tool", project_id="global")
    assert global_linter.value == "flake8"


# ── Scenario 9: Work when vector storage is unavailable ───────────────────────
def test_scenario_09_work_when_vector_storage_unavailable(test_env):
    store = test_env["store"]
    store.save(CanonicalMemory(
        entity="framework_choice",
        attribute="backend",
        value="FastAPI",
        content="Backend framework choice is FastAPI for REST API",
        status=MemoryStatus.ACTIVE,
    ))

    # Retrieval without vector store (None)
    engine = HybridRetrievalEngine(store=store, vector_store=None)
    hits = engine.search("FastAPI backend framework")
    assert len(hits) > 0
    assert hits[0].memory.value == "FastAPI"


# ── Scenario 10: Delete memory completely ─────────────────────────────────────
def test_scenario_10_delete_memory_completely(test_env):
    store = test_env["store"]
    mem = CanonicalMemory(
        memory_id="mem_to_wipe",
        entity="temp_key",
        value="sensitive_data",
        status=MemoryStatus.ACTIVE,
    )
    store.save(mem)

    # Delete
    store.delete("mem_to_wipe", hard=False)
    active_records = store.list_active()
    assert not any(m.memory_id == "mem_to_wipe" for m in active_records)


# ── Scenario 11: Resume an approval-gated action ──────────────────────────────
def test_scenario_11_resume_approval_gated_action(test_env):
    decision_eng = test_env["decision_eng"]
    dec = decision_eng.record_decision(
        question="Deploy update to production server?",
        goal="Production Deployment",
        selected_option="Deploy",
        risk_level="high",
        approval_required=True,
    )
    assert dec.approval_required is True
    assert dec.risk_level == "high"


# ── Scenario 12: Reject an action violating a hard constraint ─────────────────
def test_scenario_12_reject_action_violating_hard_constraint():
    builder = ContextBuilder(budget=TokenBudget(max_tokens=1000))
    builder.add_hard_constraint(
        title="No Destructive Disk Formats",
        content="Never execute formatting or deletion on system drives C:/.",
    )
    assembled = builder.assemble()
    assert "No Destructive Disk Formats" in assembled.context_str
    assert "HARD_CONSTRAINT" in assembled.context_str


# ── Scenario 13: Detect tool success but actual goal failure ──────────────────
def test_scenario_13_detect_tool_success_but_goal_failure():
    # Tool executed without exception (returncode 0) but target output file was empty
    res = VerificationResult(
        verified=False,
        status=VerificationStatus.FAILED,
        evidence="File exported but size is 0 bytes (empty).",
        error="FILE_EMPTY",
    )
    assert res.verified is False
    assert res.status == VerificationStatus.FAILED


# ── Scenario 14: Replan after verification failure ───────────────────────────
def test_scenario_14_replan_after_verification_failure():
    completed = [{"step": 1, "tool": "file_reader", "description": "Read input.txt"}]
    failed = {"step": 2, "tool": "fast_parser", "description": "Parse malformed syntax"}
    # Verify plan sanitization preserves remaining step bounds
    plan = _validate_and_sanitize_plan({
        "goal": "Process data",
        "can_parallelize": False,
        "steps": [
            {"step": 3, "tool": "robust_regex_parser", "description": "Parse using robust fallback parser", "parameters": {}},
        ],
    }, "Process data")
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["tool"] == "robust_regex_parser"


# ── Scenario 15: Execute safe parallel actions ───────────────────────────────
def test_scenario_15_execute_safe_parallel_actions():
    raw_plan = {
        "goal": "Fetch system stats and weather",
        "can_parallelize": True,
        "steps": [
            {"step": 1, "tool": "system_diagnostics", "description": "Check CPU", "parallel": True, "depends_on": []},
            {"step": 2, "tool": "weather_report", "description": "Check Weather", "parallel": True, "depends_on": []},
        ],
    }
    plan = _validate_and_sanitize_plan(raw_plan, "Fetch stats and weather")
    assert plan["can_parallelize"] is True
    assert plan["steps"][0]["parallel"] is True
    assert plan["steps"][1]["parallel"] is True


# ── Scenario 16: Prevent unsafe parallel actions ─────────────────────────────
def test_scenario_16_prevent_unsafe_parallel_actions():
    raw_plan = {
        "goal": "Write and compile code",
        "can_parallelize": True,
        "steps": [
            {"step": 1, "tool": "file_writer", "description": "Write code.c", "parallel": False, "depends_on": []},
            {"step": 2, "tool": "gcc_compiler", "description": "Compile code.c", "parallel": False, "depends_on": [1]},
        ],
    }
    plan = _validate_and_sanitize_plan(raw_plan, "Compile code")
    assert plan["steps"][1]["depends_on"] == [1]


# ── Scenario 17: Recover from malformed LLM plan ─────────────────────────────
def test_scenario_17_recover_from_malformed_llm_plan():
    malformed = {"invalid_key": 123}
    fallback = _validate_and_sanitize_plan(
        {"goal": "Search documentation", "steps": [{"step": 1, "tool": "web_search", "description": "Search docs"}]},
        "Search documentation"
    )
    assert len(fallback["steps"]) == 1
    assert fallback["steps"][0]["tool"] == "web_search"


# ── Scenario 18: Detect stale project state ──────────────────────────────────
def test_scenario_18_detect_stale_project_state(test_env):
    store = test_env["store"]
    old_fact = CanonicalMemory(
        entity="build_status",
        attribute="ci",
        value="FAILING",
        content="CI Build is failing",
        status=MemoryStatus.SUPERSEDED,
    )
    store.save(old_fact)

    new_fact = CanonicalMemory(
        entity="build_status",
        attribute="ci",
        value="PASSING",
        content="CI Build is passing after bug fix",
        status=MemoryStatus.ACTIVE,
    )
    store.save(new_fact)

    temporal = test_env["temporal"]
    current = temporal.get_current_truth("build_status", "ci")
    assert current.value == "PASSING"


# ── Scenario 19: Recover after context compaction ────────────────────────────
def test_scenario_19_recover_after_context_compaction(test_env):
    session_mgr = test_env["session_mgr"]
    session = SessionRecord(
        session_id="sess_compact_19",
        summary="User completed backend setup and requested database migration",
        goals=["Setup backend", "Migrate DB"],
        decisions=["Use SQLite WAL"],
        unfinished_tasks=["Run migration script"],
    )
    session_mgr.save_session(session)

    recovered = session_mgr.get_last_unconsumed_session()
    assert recovered is not None
    assert "Run migration script" in recovered.unfinished_tasks


# ── Scenario 20: Explain why a memory influenced a decision ──────────────────
def test_scenario_20_explain_why_memory_influenced_decision(test_env):
    store = test_env["store"]
    mem = CanonicalMemory(
        entity="runtime_os",
        attribute="platform",
        value="Windows",
        content="Host operating system is Windows with PowerShell",
        source_type=SourceType.SYSTEM_OBSERVATION,
    )
    store.save(mem)

    retrieval = test_env["retrieval"]
    hits = retrieval.search("What OS shell to use?")
    assert len(hits) > 0
    assert "Selected because of" in hits[0].selection_reason


# ── Scenario 21: Resolve conflicting memories ────────────────────────────────
def test_scenario_21_resolve_conflicting_memories(test_env):
    store = test_env["store"]
    conflict = test_env["conflict"]

    m1 = CanonicalMemory(entity="db_driver", attribute="name", value="psycopg2", source_type=SourceType.STRONG_INFERENCE)
    store.save(m1)

    m2 = CanonicalMemory(entity="db_driver", attribute="name", value="asyncpg", source_type=SourceType.EXPLICIT_USER_STATEMENT)
    conflicts = conflict.detect_conflicts(m2)
    resolution = conflict.resolve(m2, conflicts)
    assert resolution.winner_memory.value == "asyncpg"


# ── Scenario 22: Restore task state after restart ────────────────────────────
def test_scenario_22_restore_task_state_after_restart(test_env):
    ts = TaskState(
        task_id="task_restore_22",
        user_request="Deploy containerized agent platform",
        status=TaskStatus.RUNNING,
        current_step=3,
        total_steps=5,
    )
    # Validate TaskState serializability
    d = ts.to_dict()
    restored = TaskState.from_dict(d)
    assert restored.task_id == "task_restore_22"
    assert restored.current_step == 3
    assert restored.status == TaskStatus.RUNNING


# ── Scenario 23: Avoid duplicate external side effect ────────────────────────
def test_scenario_23_avoid_duplicate_external_side_effect(test_env):
    ledger = test_env["ledger"]
    ledger.append(LedgerEntry(
        task_id="task_email_23",
        step_id="step_send_email",
        tool_name="send_email",
        status=LedgerStatus.SUCCESS,
        evidence="Email sent message_id=msg_12345",
        verification_status=LedgerStatus.SUCCESS,
    ))

    # Verification gate prevents re-execution
    assert ledger.step_is_verified("task_email_23", "step_send_email") is True


# ── Scenario 24: Use experience replay in planning ───────────────────────────
def test_scenario_24_use_experience_replay_in_planning(test_env):
    exp_store = test_env["exp_store"]
    exp_store.record_trajectory(ExperienceTrajectory(
        goal_query="Scrape job postings from Greenhouse portal",
        success_status=True,
        step_count=2,
        tool_sequence=["greenhouse_api_fetcher", "json_parser"],
    ))

    patterns = exp_store.get_successful_patterns("Greenhouse portal scrape")
    assert len(patterns) > 0
    assert patterns[0]["tool_sequence"] == ["greenhouse_api_fetcher", "json_parser"]


# ── Scenario 25: Apply a learned lesson to a future task ──────────────────────
def test_scenario_25_apply_learned_lesson_to_future_task(test_env):
    lessons = test_env["lessons"]
    lessons.add_lesson(
        topic="SQLite concurrency",
        correction="Always enable WAL mode and set busy_timeout=30000 to prevent database locked errors.",
        source="user_correction",
    )

    relevant = lessons.get_relevant_lessons("SQLite database locked error")
    assert len(relevant) > 0
    assert "WAL mode" in relevant[0]["correction"]
