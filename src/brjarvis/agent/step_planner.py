# agent/step_planner.py — Conscious Step Planner & Adaptive Flexible Step Budget
"""
Conscious Step Planner & Adaptive Flexible Step Budget Engine for BR JARVIS.
Dynamically plans execution sub-steps and calculates flexible step budgets
that adaptively expand as long as active progress velocity is detected.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class AdaptiveStepBudget:
    """Adaptive flexible step budget controller with dynamic progress extension."""

    def __init__(self, initial_budget: int = 25, max_ceiling: int = 100):
        self.initial_budget = max(5, initial_budget)
        self.current_budget = self.initial_budget
        self.max_ceiling = max(self.initial_budget, max_ceiling)
        self.extensions_granted = 0

    def evaluate(self, current_step: int, tool_history: List[Dict[str, Any]]) -> Tuple[bool, str, bool]:
        """
        Evaluate if execution should continue given current step count and tool activity history.
        Returns (should_continue, status_message, was_extended).
        """
        if current_step < self.current_budget:
            return True, f"Step {current_step + 1}/{self.current_budget} within active budget", False

        # Check ceiling
        if self.current_budget >= self.max_ceiling:
            return False, f"Maximum step ceiling ({self.max_ceiling}) reached", False

        # Progress Velocity Assessment: Check if recent tools produced unique, valid outputs
        if not tool_history or len(tool_history) < 2:
            return False, f"Step limit ({self.current_budget}) reached with insufficient progress data", False

        recent_tools = tool_history[-5:]
        unique_tools = set(t.get("tool_name") for t in recent_tools if t.get("tool_name"))
        non_empty_results = sum(1 for t in recent_tools if t.get("result") and len(str(t.get("result")).strip()) > 10)

        # Active progress velocity -> grant flexible extension
        if non_empty_results >= 1:
            extension = 5 if self.initial_budget <= 10 else 10
            self.current_budget = min(self.max_ceiling, self.current_budget + extension)
            self.extensions_granted += 1
            msg = f"📈 Progress velocity confirmed — Granted +{extension} flexible step extension (Active Budget: {self.current_budget})"
            return True, msg, True

        return False, f"Step budget limit ({self.current_budget}) reached with low progress velocity", False


class StepPlanner:
    """Conscious step planner that decomposes user goals into structured steps and budgets."""

    @staticmethod
    def plan_steps(goal: str) -> Dict[str, Any]:
        """
        Decompose goal into conscious steps and compute dynamic initial step budget.
        """
        g_low = goal.lower().strip()

        # Classify task complexity
        is_complex = any(
            k in g_low
            for k in [
                "build",
                "scaffold",
                "refactor",
                "architecture",
                "multi",
                "parallel",
                "implement",
                "all in",
                "full",
                "complete",
                "pipeline",
                "scratchpad",
                "recreate",
                "create",
                "book",
                "startbook",
                "manual",
                "guide",
                "publication",
                "document",
                "workspace",
                "dataset",
                "longform",
                "suite",
            ]
        )
        is_medium = any(
            k in g_low
            for k in [
                "search",
                "analyze",
                "find",
                "read",
                "check",
                "inspect",
                "report",
                "edit",
                "update",
                "fix",
                "write",
                "test",
                "run",
                "generate",
            ]
        )

        if is_complex:
            initial_budget = 25
            max_ceiling = 100
            complexity = "HIGH"
            steps = [
                "Decompose high-level goal into component sub-tasks",
                "Inspect environment and workspace dependencies",
                "Execute modular implementation and file generation steps",
                "Run automated tests and empirical verification",
                "Generate walkthrough documentation",
            ]
        elif is_medium:
            initial_budget = 12
            max_ceiling = 80
            complexity = "MEDIUM"
            steps = [
                "Understand user request and locate target resources",
                "Execute tool actions and process results",
                "Verify correctness and synthesize final answer",
            ]
        else:
            initial_budget = 6
            max_ceiling = 20
            complexity = "LOW"
            steps = [
                "Execute direct user action or response",
            ]

        is_fast_path = complexity == "LOW" or any(
            k in g_low for k in ["whatsapp", "hello", "call", "open", "status", "say", "email"]
        )

        return {
            "goal": goal,
            "complexity": complexity,
            "initial_budget": initial_budget,
            "is_fast_path": is_fast_path,
            "steps": steps,
            "budget_controller": AdaptiveStepBudget(initial_budget=initial_budget, max_ceiling=max_ceiling),
        }
