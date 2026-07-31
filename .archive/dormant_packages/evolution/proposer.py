# evolution/proposer.py — Autonomous Patch Proposer
"""
Generates candidate patch proposals based on error telemetry and lesson store patterns.
Includes AST syntax tree validation to guarantee proposed code is syntax-valid Python.
"""
from __future__ import annotations

import ast
import time
import uuid
from memory.lessons import LessonStore


class PatchProposer:
    """Proposes candidate improvements or bug fixes based on system logs and feedback."""

    def __init__(self, lesson_store: LessonStore | None = None):
        self.lesson_store = lesson_store or LessonStore()

    def validate_patch_syntax(self, code: str) -> tuple[bool, str]:
        """Verify candidate patch code is valid Python syntax via AST parser."""
        try:
            ast.parse(code)
            return True, "Syntax valid"
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

    def propose_from_lessons(self) -> list[dict]:
        """Inspect lesson store and draft patch proposals for recurring issues."""
        lessons = self.lesson_store.get_latest_lessons(limit=10)
        proposals = []

        for l in lessons:
            if l.get("weight", 1.0) >= 2.0:
                patch_code = f"# Auto-generated patch based on lesson {l['id']}\n# {l['correction']}\n"
                valid, msg = self.validate_patch_syntax(patch_code)
                if valid:
                    proposal = {
                        "proposal_id": f"prop_{uuid.uuid4().hex[:8]}",
                        "title": f"Autonomy patch for {l['topic']}",
                        "reason": l["correction"],
                        "target_files": ["tools/custom_command_tools.py"],
                        "patch_code": patch_code,
                        "created_at": time.time(),
                    }
                    proposals.append(proposal)

        return proposals
