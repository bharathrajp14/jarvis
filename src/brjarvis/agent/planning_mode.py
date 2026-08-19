# agent/planning_mode.py — Antigravity-Style Planning Mode Engine
"""
Planning Mode Engine for BR JARVIS.
Evaluates goal complexity, generates implementation_plan.md and walkthrough.md,
and handles planning interlocks before major code mutations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .artifacts import ArtifactDocument, ArtifactMetadata, make_file_link


def _get_planning_dir() -> Path:
    from brjarvis.core.paths import paths

    pdir = paths.PROJECT_ROOT / "scratch"
    pdir.mkdir(parents=True, exist_ok=True)
    return pdir


class PlanningEngine:
    """Manages task complexity analysis, implementation plans, and walkthroughs."""

    _instance: Optional[PlanningEngine] = None

    def __init__(self):
        self.dir = _get_planning_dir()

    @classmethod
    def get_instance(cls) -> PlanningEngine:
        if cls._instance is None:
            cls._instance = PlanningEngine()
        return cls._instance

    def warrants_plan(self, goal: str, context: str = "") -> Tuple[bool, str]:
        """
        Evaluate if a user request warrants a formal implementation plan.
        Returns (warrants_plan: bool, reason: str).
        """
        clean = f"{goal} {context}".lower()

        # Non-planning tasks: simple queries, formatting, one-off commands, explanation
        simple_triggers = [
            "explain",
            "what is",
            "where do we",
            "how does",
            "ping",
            "system status",
            "take screenshot",
            "format table",
            "check ram",
            "read clipboard",
            "list files",
        ]
        if any(t in clean for t in simple_triggers) and len(clean.split()) < 12:
            return False, "Simple query or one-off inspection command."

        # Planning triggers: multi-file changes, architectural shifts, dev features, refactoring
        plan_triggers = [
            "implement",
            "build",
            "create feature",
            "refactor",
            "architect",
            "redesign",
            "migrate",
            "integrate",
            "add support",
            "scratchpad",
            "planning",
        ]
        for t in plan_triggers:
            if t in clean:
                return True, f"Request matches complex task trigger '{t}'."

        if len(clean.split()) > 15:
            return True, "Detailed, multi-step user request."

        return False, "Direct execution task."

    def generate_implementation_plan(
        self,
        goal: str,
        proposed_changes: List[Dict[str, Any]],
        user_review_items: List[str] = None,
        open_questions: List[str] = None,
        verification_steps: List[str] = None,
    ) -> Path:
        """
        Generate implementation_plan.md artifact document.
        """
        plan_path = self.dir / "implementation_plan.md"
        doc = ArtifactDocument(
            title=f"Implementation Plan — {goal}",
            filepath=plan_path,
            metadata=ArtifactMetadata(
                summary=f"Implementation plan for: {goal}",
                request_feedback=True,
            ),
        )

        # Overview
        doc.add_section("Goal Overview", f"Plan to accomplish: **{goal}**")

        # User Review Required
        if user_review_items:
            review_text = "\n".join(f"- {item}" for item in user_review_items)
            doc.add_alert("IMPORTANT", "Items requiring user review or approval:\n" + review_text)

        # Open Questions
        if open_questions:
            questions_text = "\n".join(f"- {q}" for q in open_questions)
            doc.add_alert("WARNING", "Open Questions:\n" + questions_text)

        # Proposed Changes
        changes_body = []
        for change in proposed_changes:
            component = change.get("component", "Core Component")
            files = change.get("files", [])
            changes_body.append(f"### {component}\n")
            for fitem in files:
                action_tag = fitem.get("tag", "MODIFY").upper()
                fpath = fitem.get("path", "")
                desc = fitem.get("description", "")
                link = make_file_link(fpath) if fpath else fitem.get("name", "file")
                changes_body.append(f"#### [{action_tag}] {link}\n{desc}\n")

        doc.add_section("Proposed Changes", "\n".join(changes_body) if changes_body else "No file changes proposed.")

        # Verification Plan
        verif_text = []
        verif_text.append("### Automated Tests")
        if verification_steps:
            for v in verification_steps:
                verif_text.append(f"- `{v}`")
        else:
            verif_text.append("- Run project unit & integration tests")

        doc.add_section("Verification Plan", "\n".join(verif_text))

        return doc.save()

    def generate_walkthrough(
        self,
        goal: str,
        accomplishments: List[str],
        test_results: List[str] = None,
    ) -> Path:
        """
        Generate walkthrough.md post-execution document.
        """
        wt_path = self.dir / "walkthrough.md"
        doc = ArtifactDocument(
            title=f"Walkthrough — {goal}",
            filepath=wt_path,
            metadata=ArtifactMetadata(
                summary=f"Walkthrough summarizing accomplishments for: {goal}",
                request_feedback=False,
            ),
        )

        # Accomplishments
        acc_text = "\n".join(f"- {a}" for a in accomplishments)
        doc.add_section("Accomplishments", acc_text if acc_text else "- Work completed successfully.")

        # Test & Validation Results
        if test_results:
            tr_text = "\n".join(f"- {tr}" for tr in test_results)
            doc.add_alert("NOTE", "Verification Results:\n" + tr_text)
            doc.add_section("Validation Summary", "All automated verification steps completed.")

        return doc.save()


def get_planning_engine() -> PlanningEngine:
    return PlanningEngine.get_instance()
