# tests/unit/test_multi_tool_orchestration.py — Comprehensive Multi-Tool Orchestration Tests
from __future__ import annotations

import os
import threading
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


from workflow.tool_orchestration import (
    ToolPlan,
    ToolStep,
    ToolCategory,
    ToolHealthStatus,
    StepExecutionStatus,
    TaskExecutionStatus,
    StepResultStore,
    ToolInputMapper,
    ToolHealthManager,
    ExecutionGraph,
    TaskCheckpointer,
    ConditionalEvaluator,
    ParallelToolExecutor,
    WorkflowExecutionReport,
    get_step_result_store,
    get_tool_health_manager,
    get_task_checkpointer,
    get_parallel_tool_executor,
)


# ── Scenario 1: Sequential Chain (A -> B -> C) with Input Mapping ─────────────

def test_sequential_chain_with_input_mapping(tmp_path):
    """Test sequential tool chain where Tool B and C consume upstream outputs via $steps.<id>.output."""
    db_path = tmp_path / "test_seq.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    execution_log = []

    def mock_runner(tool_name: str, args: dict) -> dict:
        execution_log.append((tool_name, args))
        if tool_name == "fetch_source":
            return {"source_id": "src_42", "raw_data": "sample repository text"}
        elif tool_name == "analyze_data":
            src = args.get("source_id", "")
            return {"summary": f"Analyzed {src}", "word_count": 3}
        elif tool_name == "save_report":
            return {"status": "saved", "path": "/workspace/report.docx"}
        return {"status": "ok"}

    step1 = ToolStep(
        step_id="step_fetch",
        tool="fetch_source",
        title="Fetch Source",
        parameters={"query": "test query"},
    )
    step2 = ToolStep(
        step_id="step_analyze",
        tool="analyze_data",
        title="Analyze Data",
        dependencies=["step_fetch"],
        input_mappings={"source_id": "$steps.step_fetch.output.source_id"},
    )
    step3 = ToolStep(
        step_id="step_save",
        tool="save_report",
        title="Save Report",
        dependencies=["step_analyze"],
        input_mappings={"summary": "$steps.step_analyze.output.summary"},
    )

    plan = ToolPlan(
        task_id="task_seq_001",
        goal="Sequential Analysis Pipeline",
        steps=[step1, step2, step3],
        max_concurrency=2,
    )

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
    )

    report = executor.execute_plan(plan)

    assert report.status == TaskExecutionStatus.SUCCESS_VERIFIED
    assert len(report.completed_steps) == 3
    assert len(execution_log) == 3
    assert execution_log[0][0] == "fetch_source"
    assert execution_log[1][0] == "analyze_data"
    assert execution_log[1][1]["source_id"] == "src_42"
    assert execution_log[2][0] == "save_report"
    assert execution_log[2][1]["summary"] == "Analyzed src_42"


# ── Scenario 2: Parallel Diamond Chain (A -> (B || C) -> D) ───────────────────

def test_parallel_diamond_chain(tmp_path):
    """Test parallel wave execution where independent branches B and C run concurrently."""
    db_path = tmp_path / "test_diamond.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    running_parallel = []
    concurrency_peaks = [0]
    active_count = 0
    lock = threading.Lock()

    def mock_runner(tool_name: str, args: dict) -> dict:
        nonlocal active_count
        with lock:
            active_count += 1
            concurrency_peaks[0] = max(concurrency_peaks[0], active_count)
            running_parallel.append(tool_name)

        time.sleep(0.08)  # simulate workload

        with lock:
            active_count -= 1

        return {"tool": tool_name, "status": "ok"}

    step_root = ToolStep(step_id="step_root", tool="root_task")
    step_b = ToolStep(step_id="step_b", tool="branch_b", dependencies=["step_root"])
    step_c = ToolStep(step_id="step_c", tool="branch_c", dependencies=["step_root"])
    step_join = ToolStep(step_id="step_join", tool="join_task", dependencies=["step_b", "step_c"])

    plan = ToolPlan(
        task_id="task_diamond_002",
        goal="Diamond DAG Execution",
        steps=[step_root, step_b, step_c, step_join],
        max_concurrency=4,
    )

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
        max_concurrency=4,
    )

    report = executor.execute_plan(plan)

    assert report.status == TaskExecutionStatus.SUCCESS_VERIFIED
    assert len(report.completed_steps) == 4
    # Peak concurrency during branches B and C should be 2
    assert concurrency_peaks[0] >= 2


# ── Scenario 3: Failure Branch & Recovery ─────────────────────────────────────

def test_failure_branch_and_recovery(tmp_path):
    """Test failure of primary branch triggering dynamic recovery step."""
    db_path = tmp_path / "test_recovery.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    def mock_runner(tool_name: str, args: dict) -> dict:
        if tool_name == "failing_primary":
            raise RuntimeError("Database connection timed out")
        elif tool_name == "recovery_tool":
            return {"recovery": "reconnected via replica"}
        return {"status": "ok"}

    step1 = ToolStep(
        step_id="step_primary",
        tool="failing_primary",
        is_critical=False,  # Non-critical failure allows recovery branch
    )
    step_recovery = ToolStep(
        step_id="step_recovery",
        tool="recovery_tool",
        dependencies=[],
        condition="$steps.step_primary.status == 'FAILED'",
    )

    plan = ToolPlan(
        task_id="task_recovery_003",
        goal="Failure Recovery Test",
        steps=[step1, step_recovery],
    )

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
    )

    report = executor.execute_plan(plan)

    assert "step_primary" in report.failed_steps
    assert "step_recovery" in report.completed_steps
    assert report.results["step_recovery"]["recovery"] == "reconnected via replica"


# ── Scenario 4: Conditional Branching (IF result.status) ──────────────────────

def test_conditional_branching_evaluation(tmp_path):
    """Test conditional execution predicate evaluation ($steps.<id>.status == 'SUCCESS_VERIFIED')."""
    db_path = tmp_path / "test_cond.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    executed_tools = []

    def mock_runner(tool_name: str, args: dict) -> dict:
        executed_tools.append(tool_name)
        return {"status": "success"}

    step_init = ToolStep(step_id="step_init", tool="init_check")
    # Branch True should run
    step_branch_true = ToolStep(
        step_id="step_true",
        tool="tool_true_branch",
        dependencies=["step_init"],
        condition="$steps.step_init.status == 'SUCCESS_VERIFIED'",
    )
    # Branch False should NOT run
    step_branch_false = ToolStep(
        step_id="step_false",
        tool="tool_false_branch",
        dependencies=["step_init"],
        condition="$steps.step_init.status == 'FAILED'",
    )

    plan = ToolPlan(
        task_id="task_cond_004",
        goal="Conditional Branching Test",
        steps=[step_init, step_branch_true, step_branch_false],
    )

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
    )

    report = executor.execute_plan(plan)

    assert report.status == TaskExecutionStatus.SUCCESS_VERIFIED
    assert "tool_true_branch" in executed_tools
    assert "tool_false_branch" not in executed_tools
    assert plan.steps[2].status == StepExecutionStatus.SKIPPED


# ── Scenario 5: Dynamic Replan & Expansion ────────────────────────────────────

def test_dynamic_replan_expansion():
    """Test expanding a plan dynamically with additional steps preserving completed state."""
    step1 = ToolStep(step_id="s1", tool="search", status=StepExecutionStatus.SUCCESS_VERIFIED, result={"count": 0})
    plan = ToolPlan(task_id="task_replan_005", goal="Dynamic Replan", steps=[step1])

    # Replan discovers search had 0 results, injects fetch_page and alternate search
    s2 = ToolStep(step_id="s2", tool="alternate_search", dependencies=["s1"])
    s3 = ToolStep(step_id="s3", tool="page_fetch", dependencies=["s2"])

    plan.steps.extend([s2, s3])
    graph = ExecutionGraph(plan)

    assert len(graph.steps) == 3
    ready = graph.get_ready_steps(completed_ids={"s1"}, failed_ids=set())
    assert len(ready) == 1
    assert ready[0].step_id == "s2"


# ── Scenario 6: Tool Fallback Chain ───────────────────────────────────────────

def test_tool_fallback_chain(tmp_path):
    """Test automated fallback when primary tool is unavailable or fails."""
    db_path = tmp_path / "test_fallback.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()
    health_mgr = ToolHealthManager()

    executed_tools = []

    def mock_runner(tool_name: str, args: dict) -> dict:
        executed_tools.append(tool_name)
        if tool_name == "tavily_search":
            raise ConnectionError("Tavily API quota exceeded")
        elif tool_name == "web_search":
            return {"results": ["OpenClaw architecture doc", "BR JARVIS repo"]}
        return {"status": "ok"}

    step = ToolStep(
        step_id="step_search",
        tool="tavily_search",
        category=ToolCategory.WEB_SEARCH,
        fallback_tools=["web_search", "fetch_page"],
    )

    plan = ToolPlan(
        task_id="task_fallback_006",
        goal="Fallback Test",
        steps=[step],
    )

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
        health_manager=health_mgr,
    )

    report = executor.execute_plan(plan)

    assert report.status == TaskExecutionStatus.SUCCESS_VERIFIED
    assert "tavily_search" in executed_tools
    assert "web_search" in executed_tools
    assert step.fallback_used == "web_search"
    assert len(health_mgr._fallback_records) == 1
    assert health_mgr._fallback_records[0]["primary_failed"] == "tavily_search"
    assert health_mgr._fallback_records[0]["fallback_selected"] == "web_search"


# ── Scenario 7: Checkpoint & Crash Resume ──────────────────────────────────────

def test_checkpoint_and_crash_resume(tmp_path):
    """Test state restoration from SQLite WAL and resuming execution without repeating completed steps."""
    db_path = tmp_path / "test_checkpoint.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    execution_counts = {"dangerous_payment": 0, "generate_invoice": 0}

    def mock_runner(tool_name: str, args: dict) -> dict:
        execution_counts[tool_name] = execution_counts.get(tool_name, 0) + 1
        return {"tool": tool_name, "status": "success"}

    step1 = ToolStep(step_id="step_pay", tool="dangerous_payment", is_critical=True)
    step2 = ToolStep(step_id="step_invoice", tool="generate_invoice", dependencies=["step_pay"])

    plan = ToolPlan(
        task_id="task_resume_007",
        goal="Payment and Invoice",
        steps=[step1, step2],
    )

    # Simulate Step 1 completing before a crash
    step1.status = StepExecutionStatus.SUCCESS_VERIFIED
    step1.result = {"tx_id": "tx_999"}
    execution_counts["dangerous_payment"] = 1
    checkpointer.checkpoint_plan(plan)

    # Crash & Restart: Load plan from SQLite DB
    resumed_plan = checkpointer.load_plan("task_resume_007")
    assert resumed_plan is not None
    assert resumed_plan.steps[0].status == StepExecutionStatus.SUCCESS_VERIFIED

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
    )

    report = executor.execute_plan(resumed_plan)

    assert report.status == TaskExecutionStatus.SUCCESS_VERIFIED
    assert len(report.completed_steps) == 2
    # Dangerous step 1 must NOT be re-executed
    assert execution_counts["dangerous_payment"] == 1
    assert execution_counts["generate_invoice"] == 1


# ── Scenario 8: Verification Failure Handling ─────────────────────────────────

def test_verification_failure_handling(tmp_path):
    """Test action verification rejection when tool reports success but output contains failure indicators."""
    db_path = tmp_path / "test_verif.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    def mock_runner(tool_name: str, args: dict) -> str:
        # Tool returned string containing error indicator
        return "Operation completed with SyntaxError: unexpected token in generated output"

    step = ToolStep(step_id="step_verify_fail", tool="code_helper")
    plan = ToolPlan(task_id="task_verif_008", goal="Verification Failure", steps=[step])

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
    )

    report = executor.execute_plan(plan)

    assert report.status == TaskExecutionStatus.FAILED
    assert "step_verify_fail" in report.failed_steps


# ── Scenario 9: Final Completion Predicate (SUCCESS_VERIFIED) ─────────────────

def test_final_completion_success(tmp_path):
    """Test all steps succeeding and producing SUCCESS_VERIFIED workflow report."""
    db_path = tmp_path / "test_final_success.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    def mock_runner(tool_name: str, args: dict) -> dict:
        return {"status": "ok", "evidence": f"Executed {tool_name}"}

    s1 = ToolStep(step_id="s1", tool="sys_diag")
    s2 = ToolStep(step_id="s2", tool="doc_create", dependencies=["s1"])
    s3 = ToolStep(step_id="s3", tool="open_app", dependencies=["s2"])

    plan = ToolPlan(task_id="task_final_009", goal="End-to-End Success", steps=[s1, s2, s3])

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
    )

    report = executor.execute_plan(plan)

    assert report.status == TaskExecutionStatus.SUCCESS_VERIFIED
    assert len(report.completed_steps) == 3
    assert len(report.failed_steps) == 0
    assert "Multi-Tool Execution Report" in report.summary


# ── Scenario 10: Partial Completion (PARTIAL_SUCCESS) ─────────────────────────

def test_partial_completion_reporting(tmp_path):
    """Test non-critical step failure resulting in PARTIAL_SUCCESS with precise diagnosis."""
    db_path = tmp_path / "test_partial.db"
    checkpointer = TaskCheckpointer(db_path=db_path)
    result_store = StepResultStore()

    def mock_runner(tool_name: str, args: dict) -> dict:
        if tool_name == "optional_toast":
            raise RuntimeError("Toast service not available")
        return {"status": "ok"}

    s1 = ToolStep(step_id="s1", tool="core_analysis", is_critical=True)
    s2 = ToolStep(step_id="s2", tool="doc_export", dependencies=["s1"], is_critical=True)
    s3 = ToolStep(step_id="s3", tool="optional_toast", dependencies=["s2"], is_critical=False)

    plan = ToolPlan(task_id="task_partial_010", goal="Partial Pipeline", steps=[s1, s2, s3])

    executor = ParallelToolExecutor(
        tool_runner=mock_runner,
        checkpointer=checkpointer,
        result_store=result_store,
    )

    report = executor.execute_plan(plan)

    assert report.status == TaskExecutionStatus.PARTIAL_SUCCESS
    assert "s1" in report.completed_steps
    assert "s2" in report.completed_steps
    assert "s3" in report.failed_steps
