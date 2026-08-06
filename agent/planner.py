# agent/planner.py — JARVIS MK37 Intelligent Task Planner
"""
AI-powered task planner using Gemini.
Creates structured plans with dependency tracking and parallel execution support.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _get_gemini():
    """Get GeminiBackend instance."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backends.gemini import GeminiBackend
    return GeminiBackend()


PLANNER_PROMPT = """You are JARVIS MK37's intelligent planning module. Break complex goals into smart execution steps.

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
6. For game tasks: ALWAYS use game_updater, NEVER browser_control
7. For information lookup: web_search, for current page: browser_control
8. Max 8 steps per plan

PARALLEL EXECUTION EXAMPLES:
- Searching multiple topics simultaneously
- Opening multiple apps at once
- Running independent operations

Return ONLY valid JSON:
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


def create_plan(goal: str, context: str = "") -> dict:
    """Create an intelligent execution plan for a goal."""
    try:
        gemini = _get_gemini()

        user_input = f"Goal: {goal}"
        if context:
            user_input += f"\n\nAdditional context: {context}"

        response = gemini.complete(
            messages=[{"role": "user", "content": user_input}],
            system=PLANNER_PROMPT
        )

        text = _strip_json(response)
        plan = json.loads(text)

        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Invalid plan structure")

        # Validate and clean steps
        for step in plan["steps"]:
            step.setdefault("depends_on", [])
            step.setdefault("parallel", False)
            step.setdefault("critical", True)
            # Safety: never use generated_code
            if step.get("tool") == "generated_code":
                step["tool"] = "web_search"
                step["parameters"] = {"query": step.get("description", goal)[:200]}

        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[Planner] ✅ Plan: {len(plan['steps'])} steps (parallel={plan.get('can_parallelize', False)})" }" if isinstance(f"[Planner] ✅ Plan: {len(plan['steps'])} steps (parallel={plan.get('can_parallelize', False)})", str) else f"[Planner] ✅ Plan: {len(plan['steps'])} steps (parallel={plan.get('can_parallelize', False)})")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[Planner] ✅ Plan: {len(plan['steps'])} steps (parallel={plan.get('can_parallelize', False)})" }" if isinstance(f"[Planner] ✅ Plan: {len(plan['steps'])} steps (parallel={plan.get('can_parallelize', False)})", str) else f"[Planner] ✅ Plan: {len(plan['steps'])} steps (parallel={plan.get('can_parallelize', False)})")
        for s in plan["steps"]:
            par = " [PARALLEL]" if s.get("parallel") else ""
            dep = f" [depends: {s['depends_on']}]" if s.get("depends_on") else ""
            if 'logger' in globals() or 'logger' in locals():
                logger.info(f"{ f"  Step {s['step']}: [{s['tool']}] {s['description']}{par}{dep}" }" if isinstance(f"  Step {s['step']}: [{s['tool']}] {s['description']}{par}{dep}", str) else f"  Step {s['step']}: [{s['tool']}] {s['description']}{par}{dep}")
            else:
                import logging
                logging.getLogger(__name__).info(f"{ f"  Step {s['step']}: [{s['tool']}] {s['description']}{par}{dep}" }" if isinstance(f"  Step {s['step']}: [{s['tool']}] {s['description']}{par}{dep}", str) else f"  Step {s['step']}: [{s['tool']}] {s['description']}{par}{dep}")

        return plan

    except json.JSONDecodeError as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning(f"{ f"[Planner] JSON parse failed: {e} — using fallback" }" if isinstance(f"[Planner] JSON parse failed: {e} — using fallback", str) else f"[Planner] JSON parse failed: {e} — using fallback")
        else:
            import logging
            logging.getLogger(__name__).warning(f"{ f"[Planner] JSON parse failed: {e} — using fallback" }" if isinstance(f"[Planner] JSON parse failed: {e} — using fallback", str) else f"[Planner] JSON parse failed: {e} — using fallback")
        return _fallback_plan(goal)
    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning(f"{ f"[Planner] Planning failed: {e} — using fallback" }" if isinstance(f"[Planner] Planning failed: {e} — using fallback", str) else f"[Planner] Planning failed: {e} — using fallback")
        else:
            import logging
            logging.getLogger(__name__).warning(f"{ f"[Planner] Planning failed: {e} — using fallback" }" if isinstance(f"[Planner] Planning failed: {e} — using fallback", str) else f"[Planner] Planning failed: {e} — using fallback")
        return _fallback_plan(goal)


def replan(goal: str, completed_steps: list, failed_step: dict, error: str) -> dict:
    """Replan after a failure — try a different approach."""
    try:
        gemini = _get_gemini()

        completed_summary = "\n".join(
            f"  - Step {s.get('step')}: [{s.get('tool')}] {s.get('description')} — DONE"
            for s in completed_steps
        ) or "  (none yet)"

        prompt = REPLAN_PROMPT.format(
            goal=goal,
            completed=completed_summary,
            failed_step=f"[{failed_step.get('tool')}] {failed_step.get('description')}",
            error=error[:400]
        )

        response = gemini.complete(
            messages=[{"role": "user", "content": prompt}],
            system=PLANNER_PROMPT
        )

        text = _strip_json(response)
        plan = json.loads(text)

        for step in plan.get("steps", []):
            step.setdefault("depends_on", [])
            step.setdefault("parallel", False)
            step.setdefault("critical", False)
            if step.get("tool") == "generated_code":
                step["tool"] = "web_search"
                step["parameters"] = {"query": step.get("description", goal)[:200]}

        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[Planner] 🔄 Replan: {len(plan.get('steps', []))} steps" }" if isinstance(f"[Planner] 🔄 Replan: {len(plan.get('steps', []))} steps", str) else f"[Planner] 🔄 Replan: {len(plan.get('steps', []))} steps")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[Planner] 🔄 Replan: {len(plan.get('steps', []))} steps" }" if isinstance(f"[Planner] 🔄 Replan: {len(plan.get('steps', []))} steps", str) else f"[Planner] 🔄 Replan: {len(plan.get('steps', []))} steps")
        return plan

    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning(f"{ f"[Planner] Replan failed: {e}" }" if isinstance(f"[Planner] Replan failed: {e}", str) else f"[Planner] Replan failed: {e}")
        else:
            import logging
            logging.getLogger(__name__).warning(f"{ f"[Planner] Replan failed: {e}" }" if isinstance(f"[Planner] Replan failed: {e}", str) else f"[Planner] Replan failed: {e}")
        return _fallback_plan(f"Alternative approach for: {goal}")


def _strip_json(text: str) -> str:
    """Strip markdown fences and extract JSON."""
    text = text.strip()
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    # Find JSON object
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text


def _fallback_plan(goal: str) -> dict:
    """Safe fallback plan — single web search step."""
    return {
        "goal": goal,
        "can_parallelize": False,
        "steps": [{
            "step": 1,
            "tool": "web_search",
            "description": f"Search for: {goal}",
            "parameters": {"query": goal[:200]},
            "depends_on": [],
            "parallel": False,
            "critical": True,
        }]
    }
