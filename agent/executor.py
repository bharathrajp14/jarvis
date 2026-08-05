# agent/executor.py — JARVIS MK37 Parallel Agent Executor
"""
High-performance task executor with TRUE parallel execution.
- Runs independent steps simultaneously in a thread pool
- Smart error recovery (retry, skip, replan)
- Dependency tracking for sequential steps
- Real-time progress reporting
"""
from __future__ import annotations

import concurrent.futures
import json
import logging
import re
import sys
import time
import threading
import traceback
from pathlib import Path
from typing import Callable

logger = logging.getLogger("JARVIS.AgentExecutor")


# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.planner import create_plan, replan
from agent.error_handler import analyze_error, generate_fix, ErrorDecision


# ── Tool caller ────────────────────────────────────────────────────────────

def _call_tool(tool: str, parameters: dict, speak: Callable | None = None) -> str:
    """Dispatch a tool call utilizing the centralized tool registry.
    
    All tool name aliasing (e.g., browser_control → open_app) is handled
    centrally in tools/registry.execute_tool() to avoid duplication.
    """
    from tools.registry import execute_tool
    
    params = dict(parameters or {})
    
    # Run through centralized registry (handles all aliases internally)
    result = execute_tool(tool, params)
    
    # Strict execution check — do NOT fabricate success via web search if tool is missing
    if result.startswith("ERROR: Unknown tool"):
        logger.error(f"❌ Unknown tool '{tool}' cannot be executed.")
        raise RuntimeError(f"Tool '{tool}' is not available on this system.")
        
    return result




# ── Result collector ───────────────────────────────────────────────────────

class StepResult:
    def __init__(self, step_num: int):
        self.step_num = step_num
        self.output   = ""
        self.success  = False
        self.error    = ""
        self.duration = 0.0


# ── Main Executor ──────────────────────────────────────────────────────────

class AgentExecutor:
    """
    Executes plans with parallel step execution and smart error recovery.

    Architecture:
    - Steps with no dependencies and parallel=True run simultaneously
    - Steps with depends_on wait for their dependencies to complete
    - Failed critical steps trigger replan; non-critical steps are skipped
    """

    MAX_WORKERS     = 4   # parallel threads
    MAX_REPLAN      = 2   # max replan attempts
    STEP_TIMEOUT    = 120 # seconds per step

    def execute(
        self,
        goal:        str,
        speak:       Callable | None = None,
        cancel_flag: threading.Event | None = None,
    ) -> str:
        logger.info(f"🎯 Goal: {goal}")


        replan_count   = 0
        completed_steps = []
        step_results: dict[int, str] = {}
        plan = create_plan(goal)

        while True:
            steps = plan.get("steps", [])
            if not steps:
                msg = "I couldn't create a valid plan, sir."
                if speak: speak(msg)
                return msg

            can_parallelize = plan.get("can_parallelize", False)

            # Run the plan
            result = self._run_plan(
                steps, step_results, completed_steps,
                goal, speak, cancel_flag, can_parallelize
            )

            if cancel_flag and cancel_flag.is_set():
                return "Task cancelled, sir."

            if result["success"]:
                return self._summarize(goal, completed_steps, step_results, speak)

            # Handle failure
            failed_step  = result["failed_step"]
            failed_error = result["failed_error"]

            if replan_count >= self.MAX_REPLAN:
                msg = f"Task failed after {replan_count} replan attempts, sir."
                if speak: speak(msg)
                return msg

            logger.info("Replanning (attempt %d)...", replan_count + 1)
            if speak: speak("Adjusting my approach, sir.")
            replan_count += 1
            plan = replan(goal, completed_steps, failed_step, failed_error)

    def _run_plan(
        self,
        steps:          list,
        step_results:   dict,
        completed_steps: list,
        goal:           str,
        speak:          Callable | None,
        cancel_flag:    threading.Event | None,
        can_parallelize: bool,
    ) -> dict:
        """Execute all steps in a plan, respecting dependencies and parallelism."""

        # Group steps by dependency level for parallel execution
        pending   = {s["step"]: s for s in steps}
        completed = set(step_results.keys())
        failed_step  = None
        failed_error = ""

        while pending:
            if cancel_flag and cancel_flag.is_set():
                return {"success": False, "failed_step": {}, "failed_error": "Cancelled"}

            # Find steps that are ready to run (dependencies met)
            ready = [
                s for s in pending.values()
                if all(dep in completed for dep in s.get("depends_on", []))
            ]

            if not ready:
                # Deadlock — some dependency never completed
                print("[Executor] ⚠️ Dependency deadlock — breaking remaining steps")
                break

            # Separate parallel-capable from sequential
            parallel_steps = [s for s in ready if s.get("parallel") and can_parallelize]
            seq_steps      = [s for s in ready if not s.get("parallel") or not can_parallelize]

            # Run parallel steps together, then sequential one-by-one
            if parallel_steps:
                logger.info("Running %d steps in PARALLEL", len(parallel_steps))
                results = self._run_parallel(parallel_steps, goal, speak)
                for step_num, result in results.items():
                    step = pending.pop(step_num)
                    if result.success:
                        step_results[step_num] = result.output
                        completed.add(step_num)
                        completed_steps.append(step)
                        logger.info("Step %s done (%.1fs)", step_num, result.duration)
                    else:
                        recovery = self._handle_failure(step, result.error, speak)
                        if recovery["abort"]:
                            return {"success": False, "failed_step": step, "failed_error": result.error}
                        if recovery["skip"]:
                            completed.add(step_num)
                            pending.pop(step_num, None)
                        else:
                            failed_step  = step
                            failed_error = result.error
                            return {"success": False, "failed_step": failed_step, "failed_error": failed_error}

            for step in seq_steps:
                if cancel_flag and cancel_flag.is_set():
                    return {"success": False, "failed_step": {}, "failed_error": "Cancelled"}

                step_num = step["step"]
                pending.pop(step_num)

                result = self._run_step(step, step_results, goal, speak)

                if result.success:
                    step_results[step_num] = result.output
                    completed.add(step_num)
                    completed_steps.append(step)
                    logger.info("Step %s done (%.1fs): %s", step_num, result.duration, result.output[:80])
                else:
                    recovery = self._handle_failure(step, result.error, speak)
                    if recovery["abort"]:
                        return {"success": False, "failed_step": step, "failed_error": result.error}
                    if recovery["skip"]:
                        completed.add(step_num)
                    else:
                        failed_step  = step
                        failed_error = result.error
                        return {"success": False, "failed_step": failed_step, "failed_error": failed_error}

        return {"success": True, "failed_step": None, "failed_error": ""}

    def _run_parallel(self, steps: list, goal: str, speak: Callable | None) -> dict:
        """Run multiple steps simultaneously and collect results."""
        results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as pool:
            future_to_step = {
                pool.submit(self._run_step, step, {}, goal, speak): step
                for step in steps
            }
            for future in concurrent.futures.as_completed(future_to_step, timeout=self.STEP_TIMEOUT * 2):
                step = future_to_step[future]
                try:
                    results[step["step"]] = future.result(timeout=5)
                except Exception as e:
                    r = StepResult(step["step"])
                    r.success = False
                    r.error   = str(e)
                    results[step["step"]] = r

        return results

    def _run_step(self, step: dict, context_results: dict, goal: str, speak: Callable | None) -> StepResult:
        """Execute a single step with retry logic."""
        step_num = step.get("step", "?")
        tool     = step.get("tool", "web_search")
        desc     = step.get("description", "")
        params   = dict(step.get("parameters", {}))
        result   = StepResult(step_num)

        # Inject context from previous results
        params = self._inject_context(params, tool, context_results, goal)

        logger.info("Step %s: [%s] %s", step_num, tool, desc)
        t_start = time.time()

        max_attempts = 3 if step.get("critical") else 2
        for attempt in range(1, max_attempts + 1):
            try:
                output = _call_tool(tool, params, speak)
                result.output   = output or "Done."
                result.success  = True
                result.duration = time.time() - t_start
                return result

            except Exception as e:
                err = str(e)
                logger.warning("Step %s attempt %d/%d failed: %s", step_num, attempt, max_attempts, err[:100])

                if attempt < max_attempts:
                    # Try recovery
                    recovery = analyze_error(step, err, attempt=attempt)
                    decision = recovery.get("decision")

                    if decision == ErrorDecision.RETRY:
                        time.sleep(2 ** attempt)  # exponential backoff
                        continue
                    elif decision == ErrorDecision.SKIP:
                        result.success = True
                        result.output  = f"Skipped (non-critical): {err[:60]}"
                        result.duration = time.time() - t_start
                        return result
                    elif decision == ErrorDecision.REPLAN:
                        # Try alternative tool
                        fix_suggestion = recovery.get("fix_suggestion", "")
                        if fix_suggestion and tool != "web_search":
                            try:
                                alt_step = generate_fix(step, err, fix_suggestion)
                                output = _call_tool(alt_step["tool"], alt_step["parameters"], speak)
                                result.output   = output or "Done (alternative approach)."
                                result.success  = True
                                result.duration = time.time() - t_start
                                return result
                            except Exception as fix_err:
                                print(f"[Executor] Fix also failed: {fix_err}")
                        break
                    else:  # ABORT
                        break
                else:
                    result.error = err

        result.duration = time.time() - t_start
        return result

    def _handle_failure(self, step: dict, error: str, speak: Callable | None) -> dict:
        """Decide what to do after a step failure."""
        is_critical = step.get("critical", True)
        tool        = step.get("tool", "")
        msg         = f"Step {step.get('step')} failed: {error[:80]}"

        if not is_critical:
            logger.info("Skipping non-critical step: %s", msg)
            return {"skip": True, "abort": False, "replan": False}

        # Try to determine if we should abort vs replan
        if any(kw in error.lower() for kw in ["permission", "not installed", "access denied"]):
            return {"skip": False, "abort": False, "replan": True}

        return {"skip": False, "abort": False, "replan": True}

    def _inject_context(self, params: dict, tool: str, step_results: dict, goal: str) -> dict:
        """Inject outputs from previous steps into current step parameters."""
        if not step_results:
            return params

        params = dict(params)

        # For file write operations, inject collected content
        if tool == "file_controller" and params.get("action") in ("write", "create_file"):
            if not params.get("content") or len(params.get("content", "")) < 30:
                all_results = [
                    v for v in step_results.values()
                    if v and isinstance(v, str) and len(v) > 100
                ]
                if all_results:
                    params["content"] = "\n\n---\n\n".join(all_results[:3])
                    print(f"[Executor] 💉 Injected {len(params['content'])} chars of context")

        return params

    def _summarize(
        self, goal: str, completed_steps: list,
        step_results: dict, speak: Callable | None
    ) -> str:
        """Generate a natural summary of what was accomplished."""
        fallback = (
            f"All done, sir. Completed {len(completed_steps)} steps for: {goal[:60]}."
        )

        try:
            from backends.gemini import GeminiBackend
            gemini = GeminiBackend()

            steps_str = "\n".join(
                f"  - {s.get('description', '')} [{s.get('tool', '')}]"
                for s in completed_steps[:5]
            )
            # Include actual results if available
            results_str = "\n".join(
                f"  - Step {k}: {str(v)[:100]}"
                for k, v in list(step_results.items())[:3]
            )

            prompt = (
                f'User goal: "{goal}"\n'
                f"Completed {len(completed_steps)} steps:\n{steps_str}\n\n"
                f"Key results:\n{results_str}\n\n"
                "Write ONE natural sentence summary of what was accomplished. "
                "Address the user as 'sir'. Be direct and positive. "
                "Include the most important result if available."
            )

            summary = gemini.quick(prompt)
            summary = summary.strip()[:300]

            if speak:
                speak(summary)
            return summary

        except Exception:
            if speak:
                speak(fallback)
            return fallback


# ── Multi-goal parallel executor ──────────────────────────────────────────

class ParallelGoalExecutor:
    """
    Execute MULTIPLE independent goals simultaneously.
    Use this when the user asks to do several unrelated things at once.
    """

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent

    def execute_all(
        self,
        goals: list[str],
        speak: Callable | None = None,
    ) -> dict[str, str]:
        """
        Run multiple goals in parallel. Returns {goal: result} mapping.
        """
        print(f"\n[ParallelExecutor] 🚀 Running {len(goals)} goals simultaneously")

        results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as pool:
            future_to_goal = {
                pool.submit(AgentExecutor().execute, goal, speak): goal
                for goal in goals
            }
            for future in concurrent.futures.as_completed(future_to_goal):
                goal = future_to_goal[future]
                try:
                    results[goal] = future.result(timeout=300)
                except Exception as e:
                    results[goal] = f"Failed: {e}"
                    print(f"[ParallelExecutor] ❌ Goal '{goal[:40]}': {e}")

        return results

    def execute_pipeline(
        self,
        goal: str,
        speak: Callable | None = None,
    ) -> str:
        """Execute a single goal with full parallel step support."""
        return AgentExecutor().execute(goal=goal, speak=speak)
