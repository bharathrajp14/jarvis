# agent/planner.py — Memory- & Experience-Aware Autonomous Task Planner
"""
AI-powered Task Planner for BR JARVIS.
Features:
- Dynamically loads tools from the ToolRegistry
- Ingests active constraints, user/project memory, and relevant decisions
- Retrieves past successful strategies and failure pitfalls from Experience Replay
- Enforces learned lessons to prevent repeating past mistakes
- Deterministic plan validation, cycle detection, and structured JSON output
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from brjarvis.gateway.execution import get_execution_service
from brjarvis.gateway.models_registry import TaskCapability
from brjarvis.memory.experience_replay import get_experience_replay
from brjarvis.memory.lessons import LessonStore
from brjarvis.memory.unified_memory import get_unified_memory
from brjarvis.reasoning.decision_engine import get_decision_engine
from brjarvis.router.smart_router import get_smart_router
from brjarvis.router.task_profile import TaskComplexity, TaskProfile
from brjarvis.tools.registry import get_tool_prompt_block

logger = logging.getLogger("JARVIS.Planner")


def _strip_json(text: str) -> str:
    """Extract clean JSON object from model response."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def _validate_and_sanitize_plan(raw_plan: dict, goal: str) -> dict:
    """Deterministic validation of plan structure, cycle detection, and parameter safety."""
    if not isinstance(raw_plan, dict):
        raise ValueError("Plan must be a JSON object")

    steps = raw_plan.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        raise ValueError("Plan must contain a non-empty 'steps' list")

    sanitized_steps = []
    seen_step_ids = set()

    for idx, s in enumerate(steps, start=1):
        if not isinstance(s, dict):
            continue
        step_num = s.get("step", idx)
        tool_name = str(s.get("tool", "web_search")).strip()
        desc = str(s.get("description", f"Step {idx}")).strip()
        params = s.get("parameters", {})
        if not isinstance(params, dict):
            params = {}

        deps = s.get("depends_on", [])
        if not isinstance(deps, list):
            deps = []
        # Cycle prevention: step cannot depend on itself or future steps
        valid_deps = [d for d in deps if isinstance(d, int) and d < step_num]

        sanitized_steps.append({
            "step": step_num,
            "tool": tool_name,
            "description": desc,
            "parameters": params,
            "depends_on": valid_deps,
            "parallel": bool(s.get("parallel", False)),
            "critical": bool(s.get("critical", True)),
        })
        seen_step_ids.add(step_num)

    if not sanitized_steps:
        return _fallback_plan(goal)

    return {
        "goal": str(raw_plan.get("goal", goal)),
        "can_parallelize": bool(raw_plan.get("can_parallelize", False)),
        "steps": sanitized_steps,
    }


def create_plan(
    goal: str,
    context: str = "",
    project_id: str = "global",
    constraints: Optional[List[str]] = None,
) -> dict:
    """
    Create a memory-aware, experience-informed execution plan for a goal.
    """
    try:
        um = get_unified_memory()
        exp_store = get_experience_replay()
        lessons_store = LessonStore()
        decision_eng = get_decision_engine()

        # 1. Retrieve relevant memory facts
        mem_slices = um.recall(query=goal, limit=4, project_id=project_id)
        mem_text = "\n".join([f"- [{m.get('name', 'Memory')}]: {m.get('content', '')}" for m in mem_slices])

        # 2. Retrieve past experiences (Successes and Pitfalls)
        experiences = exp_store.get_successful_patterns(goal, limit=2)
        success_text = "\n".join([f"- For goal '{e['goal_query']}': used sequence {e['tool_sequence']}" for e in experiences])

        failures = exp_store.get_similar_failures(goal, limit=2)
        failure_text = "\n".join([f"- AVOID PITFALL: For '{f['goal_query']}', {f['tool_sequence']} failed because: {f['failure_reason']}" for f in failures])

        # 3. Retrieve learned lessons
        lesson_hits = lessons_store.get_relevant_lessons(goal, limit=3)
        lessons_text = "\n".join([f"- RULE: {l.get('topic', '')} -> {l.get('correction', '')}" for l in lesson_hits])

        # 4. Ingest dynamic tool definitions
        tools_block = get_tool_prompt_block()

        # Assemble full planning prompt
        system_prompt = f"""You are BR JARVIS's master planning engine. Break complex goals into optimal, executable steps.

{tools_block}

### PLANNING DIRECTIVES:
1. Use MINIMUM steps — don't add unnecessary steps.
2. Steps can run in PARALLEL if they have no dependencies (set "parallel": true).
3. Use "depends_on": [step_number] for sequential requirements.
4. Mark "critical": true for steps that MUST succeed.
5. NEVER repeat known failure patterns. Apply learned rules and user memory.

Return ONLY valid JSON matching this schema:
{{
  "goal": "description",
  "can_parallelize": true,
  "steps": [
    {{
      "step": 1,
      "tool": "tool_name",
      "description": "what this does",
      "parameters": {{}},
      "depends_on": [],
      "parallel": false,
      "critical": true
    }}
  ]
}}"""

        user_prompt = f"Goal: {goal}\n"
        if context:
            user_prompt += f"\nContext: {context}\n"
        if mem_text:
            user_prompt += f"\nRelevant Memory Facts:\n{mem_text}\n"
        if lessons_text:
            user_prompt += f"\nActive Rules & Learned Lessons:\n{lessons_text}\n"
        if success_text:
            user_prompt += f"\nPast Successful Patterns:\n{success_text}\n"
        if failure_text:
            user_prompt += f"\nKnown Failure Pitfalls to Avoid:\n{failure_text}\n"
        if constraints:
            user_prompt += f"\nStrict Constraints:\n" + "\n".join([f"- {c}" for c in constraints]) + "\n"

        exec_service = get_execution_service()
        profile = TaskProfile(
            task_type="planning",
            complexity=TaskComplexity.HIGH if len(goal) > 100 else TaskComplexity.MEDIUM,
            requires_structured_output=True,
            requires_reasoning=True,
        )

        resp = exec_service.execute(
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt,
            json_mode=True,
            task_profile=profile,
        )
        clean_text = _strip_json(resp.text)
        raw_plan = json.loads(clean_text)

        plan = _validate_and_sanitize_plan(raw_plan, goal)
        logger.info("[Planner] Generated plan with %d steps (parallel=%s)", len(plan["steps"]), plan.get("can_parallelize", False))
        return plan

    except Exception as exc:
        logger.warning("[Planner] Planning notice (%s) — using resilient fallback plan", exc)
        return _fallback_plan(goal)


def replan(
    goal: str,
    completed_steps: list,
    failed_step: dict,
    error: str,
    project_id: str = "global",
) -> dict:
    """
    Replan after a failure — analyzes root cause and past recovery strategies.
    Preserves all verified completed steps and generates steps for remaining work only.
    """
    try:
        completed_summary = "\n".join(
            f"  - Step {s.get('step')}: [{s.get('tool')}] {s.get('description')} — VERIFIED DONE"
            for s in completed_steps
        ) or "  (none yet)"

        tools_block = get_tool_prompt_block()

        replan_system = f"""You are BR JARVIS's replanning engine. A step failed during task execution.
You must generate an alternative strategy for the REMAINING work only.

{tools_block}

### REPLANNING RULES:
1. Do NOT repeat verified completed steps.
2. Do NOT use the exact same failed tool/parameters for the failed step — adapt and use an alternative approach.
3. Return ONLY valid JSON with the standard plan schema."""

        user_prompt = f"""Goal: {goal}

Completed Verified Steps:
{completed_summary}

Failed Step: [{failed_step.get('tool')}] {failed_step.get('description')}
Error / Root Cause: {str(error)[:400]}

Generate a revised plan to complete the remaining work using a different strategy for the failed operation."""

        exec_service = get_execution_service()
        profile = TaskProfile(
            task_type="planning",
            complexity=TaskComplexity.HIGH,
            requires_structured_output=True,
            requires_reasoning=True,
        )

        resp = exec_service.execute(
            messages=[{"role": "user", "content": user_prompt}],
            system=replan_system,
            json_mode=True,
            task_profile=profile,
        )
        clean_text = _strip_json(resp.text)
        raw_plan = json.loads(clean_text)

        return _validate_and_sanitize_plan(raw_plan, goal)

    except Exception as exc:
        logger.warning("[Planner] Replanning notice (%s) — using fallback", exc)
        return _fallback_plan(goal)


def _fallback_plan(goal: str) -> dict:
    """Deterministic, resilient single-step fallback plan."""
    goal_lower = goal.lower()
    if any(k in goal_lower for k in ("search", "find", "who is", "what is", "lookup")):
        tool = "web_search"
        params = {"query": goal}
    elif any(k in goal_lower for k in ("open", "launch", "start")):
        tool = "open_app"
        params = {"app_name": goal}
    elif any(k in goal_lower for k in ("code", "python", "script", "program")):
        tool = "code_helper"
        params = {"action": "write", "description": goal}
    else:
        tool = "web_search"
        params = {"query": goal}

    return {
        "goal": goal,
        "can_parallelize": False,
        "steps": [
            {
                "step": 1,
                "tool": tool,
                "description": f"Execute: {goal}",
                "parameters": params,
                "depends_on": [],
                "parallel": False,
                "critical": True,
            }
        ],
    }
