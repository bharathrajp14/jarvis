# agent/planner_engine.py — Autonomous DAG Planner Engine for JARVIS MK37
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from brjarvis.context.engine import get_context_engine
from brjarvis.core.runtime import get_runtime
from brjarvis.events.bus import get_event_bus
from brjarvis.events.types import TaskEvent

from .types import GoalGraph, RiskLevel, StepStatus, TaskStepNode

logger = logging.getLogger("JARVIS.PlannerEngine")

# Keywords that trigger elevated risk and require human approval
DESTRUCTIVE_KEYWORDS = {
    "delete",
    "remove",
    "format",
    "push",
    "deploy",
    "drop",
    "purge",
    "purchase",
    "buy",
    "pay",
    "shutdown",
    "reboot",
    "uninstall",
    "kill",
    "wipe",
    "destroy",
    "format_disk",
}


class PlannerEngine:
    """Intelligent Directed Acyclic Graph (DAG) Task Planner Engine."""

    def __init__(self):
        self.runtime = get_runtime()
        self.context_engine = get_context_engine()
        self.event_bus = get_event_bus()

        # Register self in DI container
        self.runtime.container.register_instance(PlannerEngine, self)
        logger.info("⚡ PlannerEngine initialized")

    def _assess_risk(self, description: str, tool: str, parameters: Dict[str, Any]) -> tuple[RiskLevel, bool]:
        """Assess operational risk level and determine if explicit user approval is required."""
        text_content = f"{description} {tool} {str(parameters)}".lower()

        for kw in DESTRUCTIVE_KEYWORDS:
            if kw in text_content:
                if kw in ("format", "purge", "shutdown", "drop", "wipe"):
                    return RiskLevel.CRITICAL, True
                return RiskLevel.HIGH, True

        if tool in ("code_helper", "file_controller", "computer_control"):
            return RiskLevel.MEDIUM, False

        return RiskLevel.LOW, False

    def _validate_dag(self, steps: List[TaskStepNode]) -> None:
        """Validate DAG to guarantee no cyclic dependencies exist."""
        adj = {s.step_id: s.depends_on for s in steps}
        visited = set()
        rec_stack = set()

        def dfs(node_id: int):
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in adj.get(node_id, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    raise ValueError(f"Cyclic dependency detected in GoalGraph step #{node_id} -> #{neighbor}")
            rec_stack.remove(node_id)

        for s in steps:
            if s.step_id not in visited:
                dfs(s.step_id)

    def create_goal_graph(self, goal: str, raw_steps: List[Dict[str, Any]]) -> GoalGraph:
        """Construct a validated, risk-assessed GoalGraph DAG from plan steps."""
        steps: List[TaskStepNode] = []
        has_approval_required = False
        est_time = 0.0
        est_tokens = 250  # base cost per step

        for idx, step_data in enumerate(raw_steps, start=1):
            tool = step_data.get("tool", "agent_task")
            desc = step_data.get("description", f"Step {idx}")
            params = step_data.get("parameters", {})
            depends_on = step_data.get("depends_on", [])
            parallel = step_data.get("parallel", False)
            critical = step_data.get("critical", True)

            # Sanitize depends_on to valid step IDs < idx
            valid_depends = [d for d in depends_on if isinstance(d, int) and 1 <= d < idx]

            risk_level, requires_approval = self._assess_risk(desc, tool, params)
            if requires_approval:
                has_approval_required = True

            step_node = TaskStepNode(
                step_id=idx,
                tool=tool,
                description=desc,
                parameters=params,
                depends_on=valid_depends,
                parallel=parallel,
                critical=critical,
                risk_level=risk_level,
                requires_approval=requires_approval,
            )
            steps.append(step_node)
            est_time += 2.5
            est_tokens += 150

        # Validate DAG topology
        self._validate_dag(steps)

        graph = GoalGraph(
            goal=goal,
            steps=steps,
            can_parallelize=any(s.parallel for s in steps),
            estimated_time_s=est_time,
            estimated_token_cost=est_tokens,
            requires_user_confirmation=has_approval_required,
        )

        # Emit Event
        self.event_bus.publish(
            TaskEvent(
                topic="task.plan.created",
                task_id=graph.goal_id,
                goal=goal,
                status="planned",
                payload={"steps_count": len(steps), "requires_approval": has_approval_required},
            )
        )

        return graph

    def replan_failed_step(self, graph: GoalGraph, failed_step_id: int, error: str) -> GoalGraph:
        """Generate a revised recovery GoalGraph for remaining steps after a failure."""
        logger.warning(f"🔄 Replanning failed step #{failed_step_id} in goal [{graph.goal}]: {error}")

        new_steps: List[TaskStepNode] = []
        for s in graph.steps:
            if s.step_id < failed_step_id:
                new_steps.append(s)
            elif s.step_id == failed_step_id:
                recovery_step = s.model_copy(
                    update={
                        "description": f"Fallback recovery: {s.description}",
                        "status": StepStatus.PENDING,
                        "error": None,
                        "parameters": {**s.parameters, "_retry_fallback": True},
                    }
                )
                new_steps.append(recovery_step)
            else:
                new_steps.append(s.model_copy(update={"status": StepStatus.PENDING}))

        replanned_graph = graph.model_copy(update={"steps": new_steps})

        self.event_bus.publish(
            TaskEvent(
                topic="task.plan.replanned",
                task_id=graph.goal_id,
                goal=graph.goal,
                status="replanned",
                payload={"failed_step_id": failed_step_id, "error": error},
            )
        )

        return replanned_graph


_global_planner_engine: Optional[PlannerEngine] = None


def get_planner_engine() -> PlannerEngine:
    global _global_planner_engine
    if _global_planner_engine is None:
        _global_planner_engine = PlannerEngine()
    return _global_planner_engine
