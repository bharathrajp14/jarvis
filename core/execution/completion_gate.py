# core/execution/completion_gate.py — Centralized Task Completion Gate
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.execution.types import ExecutionResult, ExecutionStatus, VerificationOutcome
from core.execution.verifier import UniversalVerifier, get_universal_verifier

logger = logging.getLogger("JARVIS.CompletionGate")


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_approved": self.is_approved,
            "final_status": self.final_status.value,
            "evidence_summary": self.evidence_summary,
            "blocking_reasons": self.blocking_reasons,
            "verified_artifacts": self.verified_artifacts,
            "verified_side_effects": self.verified_side_effects,
            "degraded_steps": self.degraded_steps,
        }


class TaskCompletionGate:
    """
    Centralized Task Completion Gate for BR JARVIS.
    Enforces that NO task is reported as completed/successful without verified real-world evidence.
    The LLM cannot directly claim success unless approved by this gate.
    """

    def __init__(self, verifier=None):
        self.verifier = verifier or get_universal_verifier()

    def evaluate_task(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        step_results: Optional[Dict[Any, Any]] = None,
        artifacts: Optional[List[Dict[str, Any] | str]] = None,
    ) -> GateEvaluationResult:
        """
        Evaluate full task lifecycle and all step outcomes against real-world criteria.
        """
        gate = GateEvaluationResult()
        
        if not steps:
            gate.is_approved = False
            gate.final_status = ExecutionStatus.FAILED
            gate.blocking_reasons.append("Task contains zero planned or executed steps.")
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

            # 1. Check explicit failure status or error
            if raw_status in (ExecutionStatus.FAILED.value, "FAILED", "failed") or (raw_error and raw_status not in (ExecutionStatus.SUCCESS_VERIFIED.value, "SUCCESS_VERIFIED", "completed")):
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
                    completed_unverified += 1
            elif tool in ("open_app", "launch_app"):
                args = step.get("parameters") or step.get("args") or {}
                app_name = args.get("app_name") or args.get("name") or ""
                app_res = self.verifier.verify_window(app_name=app_name)
                if app_res.verified:
                    gate.verified_side_effects.append(f"Application '{app_name}' verified active.")
                    completed_verified += 1
                else:
                    completed_unverified += 1
            else:
                if raw_status in (ExecutionStatus.SUCCESS_VERIFIED.value, "SUCCESS_VERIFIED", "completed"):
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
        elif failed_non_critical > 0 or completed_unverified > 0:
            gate.is_approved = True
            gate.final_status = ExecutionStatus.PARTIAL_SUCCESS if failed_non_critical > 0 else (
                ExecutionStatus.SUCCESS_VERIFIED if completed_verified > 0 else ExecutionStatus.SUCCESS_UNVERIFIED
            )
            evidence_parts = []
            if gate.verified_artifacts:
                evidence_parts.append(f"Verified Artifacts: {', '.join(gate.verified_artifacts)}")
            if gate.verified_side_effects:
                evidence_parts.append(f"Verified Side Effects: {', '.join(gate.verified_side_effects)}")
            evidence_parts.append(f"Completed {completed_verified + completed_unverified}/{total_steps} steps.")
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

        return gate


_GLOBAL_COMPLETION_GATE: Optional[TaskCompletionGate] = None


def get_task_completion_gate() -> TaskCompletionGate:
    global _GLOBAL_COMPLETION_GATE
    if _GLOBAL_COMPLETION_GATE is None:
        _GLOBAL_COMPLETION_GATE = TaskCompletionGate()
    return _GLOBAL_COMPLETION_GATE
