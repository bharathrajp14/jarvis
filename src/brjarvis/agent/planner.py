# agent/planner.py — JARVIS Intelligent Task Planner
"""
AI-powered task planner powered by SmartModelRouter and Proxy Brain.
Creates structured plans with dependency tracking, deterministic schema validation,
and parallel execution support.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from gateway.models_registry import TaskCapability
from router.smart_router import ModelRequest, get_smart_router

logger = logging.getLogger("JARVIS.Planner")


PLANNER_PROMPT = """You are JARVIS's intelligent planning module. Break complex goals into smart execution steps.

AVAILABLE TOOLS:
open_app          → launch any application (app_name)
web_search        → search web for information (query, mode, items, aspect)
game_updater      → Steam/Epic game management (action, platform, game_name)
browser_control   → control web browser (action, url, query, text, description)
file_controller   → file/folder operations (action, path, name, content, destination)
computer_settings → OS-level controls: brightness, volume, wifi, dark mode, minimize/maximize (action, description, value)
computer_control  → mouse/keyboard automation (action, text, x, y, keys, description)
code_helper       → write/edit/run/build code (action, description, language, file_path)
dev_agent         → build complete multi-file projects (description, language, project_name)
send_message      → send messages via WhatsApp/Telegram/Discord (receiver, message_text, platform)
reminder          → set reminders (date YYYY-MM-DD, time HH:MM, message)
youtube_video     → play/summarize YouTube (action, query)
weather_report    → get weather (city)
screen_process    → analyze screen/camera (text, angle)
desktop_control   → wallpaper/organize desktop (action, path, task)
flight_finder     → search flights (origin, destination, date)
agent_task        → complex multi-step autonomous task (goal, priority)

PLANNING RULES:
1. Use MINIMUM steps — don't add unnecessary steps
2. Steps can run in PARALLEL if they have no dependencies (use "parallel": true)
3. Use "depends_on": [step_number] for sequential requirements
4. Mark "critical": true for steps that MUST succeed
5. Keep parameters clean and complete
6. Max 8 steps per plan

Return ONLY valid JSON with this schema:
{
  "goal": "description",
  "can_parallelize": true,
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "what this does",
      "parameters": {},
      "depends_on": [],
      "parallel": false,
      "critical": true
    }
  ]
}"""


REPLAN_PROMPT = """You are replanning a failed JARVIS task. Create a REVISED strategy.

Goal: {goal}
Completed steps: {completed}
Failed step: {failed_step}
Error: {error}

Generate a new plan for REMAINING work only. Do NOT repeat completed steps.
Use a DIFFERENT approach for the failed step.
Return ONLY valid JSON with the same schema."""


def _strip_json(text: str) -> str:
    """Extract JSON object from model response."""
    text = text.strip()
    # Remove markdown code fence if present
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    return text


def _validate_and_sanitize_plan(raw_plan: dict, goal: str) -> dict:
    """Deterministic validation of plan structure and parameters."""
    if not isinstance(raw_plan, dict):
        raise ValueError("Plan must be a JSON object")

    steps = raw_plan.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        raise ValueError("Plan must contain a non-empty 'steps' list")

    sanitized_steps = []
    for idx, s in enumerate(steps, start=1):
        if not isinstance(s, dict):
            continue
        tool_name = str(s.get("tool", "web_search")).strip()
        desc = str(s.get("description", f"Step {idx}")).strip()
        params = s.get("parameters", {})
        if not isinstance(params, dict):
            params = {}

        # Safety transform: map invalid or non-existent tools to safe search
        if tool_name == "generated_code":
            tool_name = "web_search"
            params = {"query": desc[:200]}

        sanitized_steps.append({
            "step": s.get("step", idx),
            "tool": tool_name,
            "description": desc,
            "parameters": params,
            "depends_on": s.get("depends_on", []) if isinstance(s.get("depends_on"), list) else [],
            "parallel": bool(s.get("parallel", False)),
            "critical": bool(s.get("critical", True)),
        })

    if not sanitized_steps:
        return _fallback_plan(goal)

    return {
        "goal": str(raw_plan.get("goal", goal)),
        "can_parallelize": bool(raw_plan.get("can_parallelize", False)),
        "steps": sanitized_steps
    }


def create_plan(goal: str, context: str = "") -> dict:
    """Create an intelligent execution plan for a goal using SmartModelRouter."""
    try:
        router = get_smart_router()

        user_input = f"Goal: {goal}"
        if context:
            user_input += f"\n\nAdditional context: {context}"

        from gateway.execution import get_execution_service
        from router.task_profile import TaskComplexity, TaskProfile

        exec_service = get_execution_service()
        profile = TaskProfile(
            task_type="planning",
            complexity=TaskComplexity.HIGH if len(goal) > 100 else TaskComplexity.MEDIUM,
            requires_structured_output=True,
            requires_reasoning=True
        )

        resp = exec_service.execute(
            messages=[{"role": "user", "content": user_input}],
            system=PLANNER_PROMPT,
            json_mode=True,
            task_profile=profile
        )
        clean_text = _strip_json(resp.text)
        raw_plan = json.loads(clean_text)

        plan = _validate_and_sanitize_plan(raw_plan, goal)

        logger.info("[Planner] Generated plan: %d steps (parallel=%s)", len(plan["steps"]), plan.get("can_parallelize", False))
        return plan

    except Exception as exc:
        logger.warning("[Planner] Planning notice (%s) — using resilient fallback plan", exc)
        return _fallback_plan(goal)



def replan(goal: str, completed_steps: list, failed_step: dict, error: str) -> dict:
    """Replan after a failure — try a different approach."""
    try:
        router = get_smart_router()

        completed_summary = "\n".join(
            f"  - Step {s.get('step')}: [{s.get('tool')}] {s.get('description')} — DONE"
            for s in completed_steps
        ) or "  (none yet)"

        prompt = REPLAN_PROMPT.format(
            goal=goal,
            completed=completed_summary,
            failed_step=f"[{failed_step.get('tool')}] {failed_step.get('description')}",
            error=str(error)[:400]
        )

        from gateway.execution import get_execution_service
        from router.task_profile import TaskComplexity, TaskProfile

        exec_service = get_execution_service()
        profile = TaskProfile(
            task_type="planning",
            complexity=TaskComplexity.HIGH,
            requires_structured_output=True,
            requires_reasoning=True
        )

        resp = exec_service.execute(
            messages=[{"role": "user", "content": prompt}],
            system=PLANNER_PROMPT,
            json_mode=True,
            task_profile=profile
        )
        clean_text = _strip_json(resp.text)
        raw_plan = json.loads(clean_text)

        return _validate_and_sanitize_plan(raw_plan, goal)


    except Exception as exc:
        logger.warning("[Planner] Replanning notice (%s) — using fallback", exc)
        return _fallback_plan(goal)


def _fallback_plan(goal: str) -> dict:
    """Deterministic, resilient single/two-step fallback plan."""
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
                "critical": True
            }
        ]
    }
