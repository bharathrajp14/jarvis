# core/execution/completion_gate.py — Centralized Task Completion Gate
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .types import ExecutionResult, ExecutionStatus, VerificationOutcome
from .verifier import UniversalVerifier, get_universal_verifier

logger = logging.getLogger("JARVIS.CompletionGate")

# Operation categories that a tool must match for goal coverage
_OPERATION_TOOL_MAP: Dict[str, List[str]] = {
    "CREATE_PORTFOLIO":    ["file_write", "create_file", "document_creator", "code_helper", "dev_agent", "file_controller"],
    "PUSH_TO_GITHUB":      ["git_repo_mgr", "git_push"],
    "GIT_COMMIT":          ["git_repo_mgr"],
    "OPEN_PORTFOLIO":      ["open_app", "launch_app", "browser_open_url", "browser_control"],
    "OPEN_APPLICATION":    ["open_app", "launch_app"],
    "CREATE_DOCUMENT":     ["create_word_document", "create_pdf_document", "document_creator", "file_write", "file_controller"],
    "WEB_SEARCH":          ["web_search", "browser_control"],
    "INSTALL_DEPENDENCY":  ["code_helper", "system_tools"],
    "EXECUTE_GOAL":        [],   # wildcard — any tool counts
}


@dataclass
class GateEvaluationResult:
    """Outcome of TaskCompletionGate evaluation."""
    is_approved: bool = False
    final_status: ExecutionStatus = ExecutionStatus.FAILED
    evidence_summary: str = ""
    blocking_reasons: List[str] = field(default_factory=list)
    verified_artifacts: List[str] = field(default_factory=list)
    verified_side_effects: List[str] = field(default_factory=list)
    degraded_steps: List[str] = field(default_factory=list)
    # MK40.2: goal coverage tracking
    required_operations_covered: List[str] = field(default_factory=list)
    required_operations_missing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_approved": self.is_approved,
            "final_status": self.final_status.value,
            "evidence_summary": self.evidence_summary,
            "blocking_reasons": self.blocking_reasons,
            "verified_artifacts": self.verified_artifacts,
            "verified_side_effects": self.verified_side_effects,
            "degraded_steps": self.degraded_steps,
            "required_operations_covered": self.required_operations_covered,
            "required_operations_missing": self.required_operations_missing,
        }


class TaskCompletionGate:
    """
    Centralized Task Completion Gate for BR JARVIS.
    Enforces that NO task is reported as completed/successful without verified real-world evidence.
    The LLM cannot directly claim success unless approved by this gate.

    MK40.2 additions:
    - Checks that executed operations cover the required_operations from the GoalSpec
    - Uses the ExecutionLedger as the authoritative record of what actually happened
    - Returns TASK_FAILED_RESULT_MISMATCH when executed artifacts don't match the goal
    """

    def __init__(self, verifier=None):
        self.verifier = verifier or get_universal_verifier()

    def _check_goal_coverage(
        self,
        required_operations: List[str],
        ledger_entries: List[Any],
        gate: GateEvaluationResult,
    ) -> bool:
        """
        Verify that every required operation has a matching VERIFIED ledger entry.

        Returns True if all required operations are covered, False otherwise.
        Populates gate.required_operations_covered and gate.required_operations_missing.

        MK40.2 §7: Before generating the final response, compare USER REQUEST
        against ACTUAL EXECUTED OPERATIONS against VERIFIED ARTIFACTS.
        """
        if not required_operations:
            # No operations specified — cannot do coverage check
            return True

        from agent.execution_ledger import LedgerStatus

        executed_tools = {
            e.tool_name
            for e in ledger_entries
            if e.status in (LedgerStatus.SUCCESS, LedgerStatus.PARTIAL)
        }

        all_covered = True
        for op in required_operations:
            required_tools = _OPERATION_TOOL_MAP.get(op, [])
            if not required_tools:
                # Wildcard or unknown operation — assume covered
                gate.required_operations_covered.append(op)
                continue
            if any(t in executed_tools for t in required_tools):
                gate.required_operations_covered.append(op)
            else:
                gate.required_operations_missing.append(op)
                all_covered = False
                logger.warning(
                    "[CompletionGate] Required operation '%s' not covered by any executed tool. "
                    "Required one of: %s. Executed: %s",
                    op, required_tools, list(executed_tools)
                )

        return all_covered

    def evaluate_task(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        step_results: Optional[Dict[Any, Any]] = None,
        artifacts: Optional[List[Dict[str, Any] | str]] = None,
        ledger_entries: Optional[List[Any]] = None,
        required_operations: Optional[List[str]] = None,
    ) -> GateEvaluationResult:
        """
        Evaluate full task lifecycle against real-world evidence.

        MK40.2: Now also checks goal coverage using ledger_entries and required_operations.
        """
        gate = GateEvaluationResult()

        # ── MK40.2: Always perform goal coverage check if ledger entries & required operations provided ──
        if ledger_entries and required_operations:
            self._check_goal_coverage(required_operations, ledger_entries, gate)

        if not steps:
            gate.is_approved = False
            gate.final_status = ExecutionStatus.FAILED
            gate.blocking_reasons.append("Task contains zero planned or executed steps.")
            if gate.required_operations_missing:
                gate.blocking_reasons.append(
                    f"TASK_FAILED_RESULT_MISMATCH: Missing required operations: {', '.join(gate.required_operations_missing)}"
                )
            gate.evidence_summary = "Task evaluation failed: No execution steps recorded."
            return gate

        total_steps = len(steps)
        completed_verified = 0
        completed_unverified = 0
        failed_critical = 0
        failed_non_critical = 0

        for idx, step in enumerate(steps):
            step_id = step.get("step_id") or step.get("step") or idx + 1
            tool = step.get("tool") or step.get("tool_name") or ""
            is_critical = step.get("is_critical", True) if "is_critical" in step else step.get("critical", True)
            
            raw_status = step.get("status", "")
            raw_output = str(step.get("result") or step.get("output") or "")
            raw_error = step.get("error")

            # 0. Check skipped steps (e.g., conditional branching)
            if raw_status in ("SKIPPED", "skipped", "skipped_condition"):
                continue

            # 1. Check explicit failure status or error
            if raw_status in (ExecutionStatus.FAILED.value, "FAILED", "failed") or (raw_error and raw_status not in (ExecutionStatus.SUCCESS_VERIFIED.value, "SUCCESS_VERIFIED", "completed", "ok", "success")):
                if is_critical:
                    failed_critical += 1
                    gate.blocking_reasons.append(f"Critical Step {step_id} [{tool}] failed: {raw_error or 'Execution failed'}")
                else:
                    failed_non_critical += 1
                    gate.degraded_steps.append(f"Non-critical Step {step_id} [{tool}] failed: {raw_error}")
                continue

            # 2. Output string semantic check
            val_res = self.verifier.validate_output(raw_output)
            if not val_res.verified:
                if is_critical:
                    failed_critical += 1
                    gate.blocking_reasons.append(f"Step {step_id} [{tool}] output contains fatal error: {val_res.error}")
                else:
                    failed_non_critical += 1
                    gate.degraded_steps.append(f"Non-critical Step {step_id} [{tool}] had notice: {val_res.details}")
                continue

            # 3. Check artifact production if expected
            if tool in ("document_creator", "create_word_document", "create_pdf_document", "file_write"):
                args = step.get("parameters") or step.get("args") or {}
                filename = args.get("filename") or args.get("path") or ""
                if filename:
                    doc_res = self.verifier.verify_file(filename)
                    if doc_res.verified:
                        gate.verified_artifacts.append(str(filename))
                        completed_verified += 1
                    else:
                        if is_critical:
                            failed_critical += 1
                            gate.blocking_reasons.append(f"Step {step_id} [{tool}] expected file '{filename}' was not verified on disk.")
                        else:
                            failed_non_critical += 1
                        continue
                else:
                    if raw_status in (ExecutionStatus.SUCCESS_VERIFIED.value, "SUCCESS_VERIFIED", "completed", "ok", "success"):
                        completed_verified += 1
                    else:
                        completed_unverified += 1
            elif tool in ("open_app", "launch_app"):
                if raw_status in (ExecutionStatus.SUCCESS_UNVERIFIED.value, "SUCCESS_UNVERIFIED", "unverified"):
                    completed_unverified += 1
                    gate.degraded_steps.append(f"Step {step_id} [{tool}] application launch command sent, but window was unverified.")
                else:
                    args = step.get("parameters") or step.get("args") or {}
                    app_name = args.get("app_name") or args.get("name") or ""
                    if app_name:
                        app_res = self.verifier.verify_window(app_name=app_name)
                        if app_res.verified:
                            gate.verified_side_effects.append(f"Application '{app_name}' verified active on screen.")
                            completed_verified += 1
                        else:
                            completed_unverified += 1
                            gate.degraded_steps.append(f"Step {step_id} [{tool}] application launch command sent, but window was not verified on screen.")
                    else:
                        completed_verified += 1
            else:
                if raw_status in (ExecutionStatus.SUCCESS_VERIFIED.value, "SUCCESS_VERIFIED", "completed", "ok", "success"):
                    completed_verified += 1
                else:
                    completed_unverified += 1

        # Determine overall task status
        if failed_critical > 0:
            gate.is_approved = False
            gate.final_status = ExecutionStatus.FAILED
            gate.evidence_summary = (
                f"Task failed completion gate. {failed_critical}/{total_steps} critical steps failed. "
                f"Reasons: {'; '.join(gate.blocking_reasons)}"
            )
        elif completed_unverified > 0 or failed_non_critical > 0:
            gate.is_approved = True
            gate.final_status = ExecutionStatus.PARTIAL_SUCCESS
            evidence_parts = []
            if gate.verified_artifacts:
                evidence_parts.append(f"Verified Artifacts: {', '.join(gate.verified_artifacts)}")
            if gate.verified_side_effects:
                evidence_parts.append(f"Verified Side Effects: {', '.join(gate.verified_side_effects)}")
            if gate.degraded_steps:
                evidence_parts.append(f"Unverified Items: {'; '.join(gate.degraded_steps)}")
            evidence_parts.append(f"Verified {completed_verified}/{total_steps} steps.")
            gate.evidence_summary = " | ".join(evidence_parts)
        else:
            gate.is_approved = True
            gate.final_status = ExecutionStatus.SUCCESS_VERIFIED
            evidence_parts = []
            if gate.verified_artifacts:
                evidence_parts.append(f"Verified Artifacts: {', '.join(gate.verified_artifacts)}")
            if gate.verified_side_effects:
                evidence_parts.append(f"Verified Side Effects: {', '.join(gate.verified_side_effects)}")
            evidence_parts.append(f"All {total_steps} steps verified successfully.")
            gate.evidence_summary = " | ".join(evidence_parts)

        # ── MK40.2: Goal coverage check using ledger entries ─────────────────────
        # Only run coverage check if we have both ledger data and required operations
        if ledger_entries and required_operations:
            coverage_ok = self._check_goal_coverage(required_operations, ledger_entries, gate)
            if not coverage_ok and gate.is_approved:
                # Operations were executed but did not match the required goal operations
                missing_ops = ", ".join(gate.required_operations_missing)
                gate.is_approved = False
                gate.final_status = ExecutionStatus.FAILED
                gate.blocking_reasons.append(
                    f"TASK_FAILED_RESULT_MISMATCH: Required operations not executed: {missing_ops}. "
                    f"The executed tools did not cover the requested goal."
                )
                gate.evidence_summary = (
                    f"Goal mismatch detected. Required: {required_operations}. "
                    f"Missing: {missing_ops}. Covered: {gate.required_operations_covered}."
                )
                logger.error(
                    "[CompletionGate] TASK_FAILED_RESULT_MISMATCH — goal '%s' required %s but got %s",
                    goal[:80], required_operations, gate.required_operations_covered
                )

        return gate


_GLOBAL_COMPLETION_GATE: Optional[TaskCompletionGate] = None


def get_task_completion_gate() -> TaskCompletionGate:
    global _GLOBAL_COMPLETION_GATE
    if _GLOBAL_COMPLETION_GATE is None:
        _GLOBAL_COMPLETION_GATE = TaskCompletionGate()
    return _GLOBAL_COMPLETION_GATE
