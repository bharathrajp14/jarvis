# agent/goal_decomposer.py — BR JARVIS MK40.2 Goal Decomposition Engine
"""
Converts a user's natural-language goal into an explicit, structured GoalSpec
before any execution begins.

The GoalSpec defines:
  - required_operations: high-level operations that MUST succeed
  - acceptance_criteria: discrete verifiable checkpoints
  - tool_dag: directed acyclic graph of tool dependencies

The original user_request is NEVER modified. The GoalSpec is derived from it
and stored alongside the TaskState. If the CompletionGate detects that the
executed operations do not match the required_operations, it returns
TASK_FAILED_RESULT_MISMATCH regardless of individual step success.

Goal preservation rule (§2 of MK40.2 spec):
    USER: "Create a portfolio and push it to GitHub, then open it."
    REQUIRED: CREATE_PORTFOLIO + PUSH_TO_GITHUB + OPEN_PORTFOLIO

    The agent MUST NOT substitute:
        "create an architecture audit document"
        or "analyze GitHub"
        or "open browser"
    as completion of this goal.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.GoalDecomposer")


# ── Data contracts ─────────────────────────────────────────────────────────────

@dataclass
class Criterion:
    """A single discrete, verifiable acceptance criterion."""
    criterion_id:      str    # e.g. "C1", "C2"
    description:       str    # human-readable
    required:          bool = True
    tool_categories:   List[str] = field(default_factory=list)  # e.g. ["git", "filesystem"]
    verification_method: str = "tool_output"  # "file_exists" | "process_running" | "tool_output" | "remote_verified"
    status:            str = "PENDING"  # PENDING | VERIFIED | FAILED | UNVERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Criterion":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class GoalSpec:
    """
    Structured decomposition of a user goal.

    This is computed ONCE before execution and stored immutably in TaskState.
    It is the contract against which the CompletionGate measures actual results.
    """
    original_request:    str
    required_operations: List[str]           # e.g. ["CREATE_PORTFOLIO", "PUSH_TO_GITHUB"]
    acceptance_criteria: List[Criterion]
    tool_dag:            Dict[str, List[str]] = field(default_factory=dict)
    decomposed_by:       str = "llm"         # "llm" | "deterministic"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["acceptance_criteria"] = [c.to_dict() for c in self.acceptance_criteria]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GoalSpec":
        raw = dict(d)
        raw["acceptance_criteria"] = [
            Criterion.from_dict(c) if isinstance(c, dict) else c
            for c in raw.get("acceptance_criteria", [])
        ]
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


# ── LLM-based decomposer ──────────────────────────────────────────────────────

_DECOMPOSE_SYSTEM_PROMPT = """You are the goal analysis module for BR JARVIS.

Given a user request, extract the required high-level operations and verification criteria.

Return ONLY valid JSON in this exact schema:
{
  "required_operations": ["OPERATION_A", "OPERATION_B"],
  "acceptance_criteria": [
    {
      "criterion_id": "C1",
      "description": "what must be true",
      "required": true,
      "tool_categories": ["filesystem"],
      "verification_method": "file_exists"
    }
  ],
  "tool_dag": {
    "OPERATION_A": [],
    "OPERATION_B": ["OPERATION_A"]
  }
}

verification_method values: file_exists | process_running | tool_output | remote_verified | user_confirmed
tool_categories values: filesystem | git | github | browser | system | network | document | code | email

IMPORTANT:
- Be precise. "Create a portfolio" requires CREATE_PORTFOLIO, not ANALYZE_PROJECTS.
- "Push to GitHub" requires PUSH_TO_GITHUB with remote_verified criterion, not just git commit.
- "Open it" requires OPEN_APPLICATION with process_running criterion.
- Never substitute an unrelated operation for a required one."""


def _strip_json(text: str) -> str:
    text = text.strip()
    m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if m:
        return m.group(1).strip()
    # Try to find first { ... }
    m = re.search(r'\{[\s\S]+\}', text)
    return m.group(0) if m else text


def _decompose_via_llm(goal: str) -> Optional[GoalSpec]:
    """Attempt LLM-based decomposition. Returns None on any failure."""
    try:
        from gateway.execution import get_execution_service
        from router.task_profile import TaskComplexity, TaskProfile

        exec_service = get_execution_service()
        profile = TaskProfile(
            task_type="analysis",
            complexity=TaskComplexity.MEDIUM,
            requires_structured_output=True,
            requires_reasoning=True,
        )
        resp = exec_service.execute(
            messages=[{"role": "user", "content": f"User request: {goal}"}],
            system=_DECOMPOSE_SYSTEM_PROMPT,
            json_mode=True,
            task_profile=profile,
        )
        raw = json.loads(_strip_json(resp.text))

        criteria = [
            Criterion(
                criterion_id=c.get("criterion_id", f"C{i+1}"),
                description=c.get("description", ""),
                required=bool(c.get("required", True)),
                tool_categories=list(c.get("tool_categories", [])),
                verification_method=str(c.get("verification_method", "tool_output")),
            )
            for i, c in enumerate(raw.get("acceptance_criteria", []))
        ]

        return GoalSpec(
            original_request=goal,
            required_operations=list(raw.get("required_operations", [])),
            acceptance_criteria=criteria,
            tool_dag=raw.get("tool_dag", {}),
            decomposed_by="llm",
        )
    except Exception as exc:
        logger.warning("[GoalDecomposer] LLM decomposition failed (%s), using deterministic fallback", exc)
        return None


# ── Deterministic keyword-based fallback ──────────────────────────────────────

# Maps goal keyword patterns to required operations and criteria
_KEYWORD_RULES: List[tuple] = [
    # (regex, required_operation, criteria_list)
    (
        r"\b(portfolio|personal site|personal website|resume site)\b",
        "CREATE_PORTFOLIO",
        [
            Criterion("C_PORT_1", "Portfolio source files exist on disk", True, ["filesystem"], "file_exists"),
            Criterion("C_PORT_2", "Portfolio content is valid (non-empty)", True, ["filesystem"], "file_exists"),
        ],
    ),
    (
        r"\b(push|upload|deploy).*(github|git hub|remote|repo)\b",
        "PUSH_TO_GITHUB",
        [
            Criterion("C_GIT_1", "Git repository initialized or identified", True, ["git"], "tool_output"),
            Criterion("C_GIT_2", "Files staged and committed", True, ["git"], "tool_output"),
            Criterion("C_GIT_3", "GitHub authentication available", True, ["git", "github"], "tool_output"),
            Criterion("C_GIT_4", "Push command executed with returncode 0", True, ["git"], "tool_output"),
            Criterion("C_GIT_5", "Remote branch updated (verified via ls-remote)", True, ["git", "github"], "remote_verified"),
        ],
    ),
    (
        r"\b(open|view|launch|show)\b.*(portfolio|site|file|document|it|result)\b",
        "OPEN_PORTFOLIO",
        [
            Criterion("C_OPEN_1", "Correct application launched", True, ["browser", "system"], "process_running"),
            Criterion("C_OPEN_2", "Correct document is active in application", True, ["browser", "system"], "process_running"),
        ],
    ),
    (
        r"\b(commit|stage|add)\b",
        "GIT_COMMIT",
        [
            Criterion("C_COM_1", "Git commit created with non-empty hash", True, ["git"], "tool_output"),
        ],
    ),
    (
        r"\b(create|write|generate|build|make)\b.*(document|report|docx|pdf|file)\b",
        "CREATE_DOCUMENT",
        [
            Criterion("C_DOC_1", "Document file exists on disk", True, ["filesystem"], "file_exists"),
            Criterion("C_DOC_2", "Document is non-empty and parseable", True, ["filesystem"], "file_exists"),
        ],
    ),
    (
        r"\b(search|find|look up|lookup|who is|what is)\b",
        "WEB_SEARCH",
        [
            Criterion("C_WEB_1", "Search returned results", True, ["network"], "tool_output"),
        ],
    ),
    (
        r"\b(install|pip install|npm install|setup|configure)\b",
        "INSTALL_DEPENDENCY",
        [
            Criterion("C_INST_1", "Installation completed without error", True, ["system"], "tool_output"),
        ],
    ),
]


def _decompose_deterministic(goal: str) -> GoalSpec:
    """
    Deterministic keyword-based goal decomposition.
    Always produces a valid GoalSpec — used as fallback when LLM fails.
    """
    goal_lower = goal.lower()
    operations = []
    criteria = []
    dag: Dict[str, List[str]] = {}
    prev_op = None

    for pattern, operation, op_criteria in _KEYWORD_RULES:
        if re.search(pattern, goal_lower, re.IGNORECASE):
            operations.append(operation)
            criteria.extend(op_criteria)
            # Build simple linear DAG
            dag[operation] = [prev_op] if prev_op else []
            prev_op = operation

    if not operations:
        # Absolute fallback — generic single operation
        operations = ["EXECUTE_GOAL"]
        criteria = [Criterion("C_GENERIC_1", f"Goal executed: {goal[:100]}", True, [], "tool_output")]
        dag = {"EXECUTE_GOAL": []}

    return GoalSpec(
        original_request=goal,
        required_operations=operations,
        acceptance_criteria=criteria,
        tool_dag=dag,
        decomposed_by="deterministic",
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def decompose_goal(goal: str) -> GoalSpec:
    """
    Convert a user goal string into a structured GoalSpec.

    Tries LLM-based decomposition first for richer analysis; falls back to
    deterministic keyword matching if the LLM call fails.

    The returned GoalSpec is stored in TaskState.acceptance_criteria and used
    by the CompletionGate to verify actual results against the stated goal.
    """
    if not goal or not goal.strip():
        return GoalSpec(
            original_request=goal,
            required_operations=["EXECUTE_GOAL"],
            acceptance_criteria=[],
            decomposed_by="deterministic",
        )

    spec = _decompose_via_llm(goal)
    if spec and spec.required_operations:
        logger.info("[GoalDecomposer] LLM decomposed goal into %d operations: %s",
                    len(spec.required_operations), spec.required_operations)
        return spec

    spec = _decompose_deterministic(goal)
    logger.info("[GoalDecomposer] Deterministic decomposed goal into %d operations: %s",
                len(spec.required_operations), spec.required_operations)
    return spec
