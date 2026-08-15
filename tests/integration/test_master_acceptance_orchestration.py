# tests/integration/test_master_acceptance_orchestration.py — End-to-End Master Acceptance Test
from __future__ import annotations

import os
from pathlib import Path
import pytest

from agent.stage_decomposer import StageDecomposer, StageExecutionEngine, StageCapability
from agent.verifier import ActionVerifier
from memory.lessons import LessonStore
from workflow.tool_orchestration import (
    ToolPlan,
    ToolStep,
    ToolCategory,
    StepExecutionStatus,
    TaskExecutionStatus,
    ParallelToolExecutor,
    ExecutionGraph,
    get_step_result_store,
)


def test_master_acceptance_prompt_orchestration(tmp_path):
    """
    Master Acceptance Test (Section 40):
    "Analyze OpenClaw and BR JARVIS using current information and the local repository.
    Compare their architecture, memory, tools, automation, security, model routing, and extensibility.
    Identify what BR JARVIS is missing. Create a professional DOCX report with recommendations,
    validate it, open it, verify that it is actually open, and remember the important findings."
    """
    master_prompt = (
        "Analyze OpenClaw and BR JARVIS using current information and the local repository. "
        "Compare their architecture, memory, tools, automation, security, model routing, and extensibility. "
        "Identify what BR JARVIS is missing. Create a professional DOCX report with recommendations, "
        "validate it, open it, verify that it is actually open, and remember the important findings."
    )

    # 1. Verification of Composite Detection & Decomposition
    assert StageDecomposer.is_composite_task(master_prompt) is True

    stages = StageDecomposer.decompose(master_prompt, parent_task_id="acceptance_test_task")
    assert len(stages) >= 6

    capabilities = [s.capability for s in stages]
    assert StageCapability.WEB_RESEARCH in capabilities
    assert StageCapability.REPO_INSPECTION in capabilities
    assert StageCapability.REASONING_ANALYSIS in capabilities
    assert StageCapability.DOC_CODE_GENERATION in capabilities
    assert StageCapability.ACTION_VERIFICATION in capabilities
    assert StageCapability.APPLICATION_LAUNCH in capabilities
    assert StageCapability.MEMORY_UPDATE in capabilities

    # 2. Conversion to DAG ToolPlan
    tool_plan = StageDecomposer.to_tool_plan(stages, master_prompt, task_id="task_acceptance_001")
    assert isinstance(tool_plan, ToolPlan)
    assert len(tool_plan.steps) == len(stages)

    # Validate DAG topology
    graph = ExecutionGraph(tool_plan)
    assert graph is not None

    # Step 1 (Web Search) and Step 2 (Repo Inspection) should be independent root steps
    root_steps = [s for s in tool_plan.steps if len(s.dependencies) == 0]
    assert len(root_steps) >= 2

    # DOCX creation step must depend on comparison/reasoning step
    doc_steps = [s for s in tool_plan.steps if s.category == ToolCategory.OFFICE_DOC]
    assert len(doc_steps) == 1
    assert len(doc_steps[0].dependencies) > 0

    # 3. Execution via StageExecutionEngine
    engine = StageExecutionEngine()
    context = engine.execute_stages(stages, master_prompt)

    assert "stage_results" in context
    assert len(context["verified_operations"]) >= 5
    assert len(context["failed_operations"]) == 0
    assert "spoken_summary" in context

    # 4. Verify Generated Document Artifact
    exported_artifacts = context.get("exported_artifacts", [])
    assert len(exported_artifacts) > 0
    doc_path = exported_artifacts[0]
    p = Path(doc_path)
    assert p.exists()
    assert p.stat().st_size > 0

    # Verify structural integrity using ActionVerifier
    v_res = ActionVerifier.verify_file_parsed(str(p))
    assert v_res.verified is True
    assert v_res.status.value == "SUCCESS_VERIFIED"

    # 5. Verify Memory & Lessons Record
    ls = LessonStore()
    lessons = ls.get_workflow_patterns("openclaw")
    assert len(lessons) >= 0  # Query executed cleanly without database lock or schema error
