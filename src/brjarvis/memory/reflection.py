# memory/reflection.py — Behavioral & Code Reflection Engine
"""
ReflectionEngine for analyzing user feedback, implicit re-prompts, tool failures,
and failed steps, automatically writing extracted lessons to LessonStore.
"""

from __future__ import annotations

import re

from .lessons import LessonStore


class ReflectionEngine:
    """Monitors turns and task outcomes to automatically extract self-corrective lessons."""

    def __init__(self, lesson_store: LessonStore | None = None):
        self.lesson_store = lesson_store or LessonStore()

    def process_turn(self, user_input: str, previous_output: str, elapsed_since_last_sec: float = 0) -> dict | None:
        """
        Analyze dialogue turn for explicit or implicit user corrections, or negative feedback.
        """
        clean_in = user_input.strip().lower()

        # 1. Explicit correction patterns
        explicit_patterns = [
            r"no,?\s+(?:don't|do not|instead)\s+(.+)",
            r"wrong,?\s+(.+)",
            r"stop\s+doing\s+(.+)",
            r"always\s+(?:use|do|make)\s+(.+)",
            r"never\s+(?:use|do|make)\s+(.+)",
            r"that's\s+not\s+(?:what|how)\s+(.+)",
            r"incorrect,?\s+(.+)",
            r"don't\s+(?:use|do|create|run)\s+(.+)",
        ]

        for pat in explicit_patterns:
            m = re.search(pat, clean_in)
            if m:
                correction = user_input.strip()
                topic = m.group(1).strip()[:80]
                lesson_id = self.lesson_store.add_lesson(
                    topic=topic,
                    correction=correction,
                    source="explicit",
                    weight=2.0,
                )
                return {
                    "type": "explicit_correction",
                    "lesson_id": lesson_id,
                    "topic": topic,
                    "correction": correction,
                }

        # 2. Implicit correction (user re-prompts immediately after turn within 60s)
        if 0 < elapsed_since_last_sec <= 60 and any(
            kw in clean_in for kw in ["redo", "try again", "fix this", "do it again", "same result", "it failed"]
        ):
            topic = user_input[:50]
            lesson_id = self.lesson_store.add_lesson(
                topic=topic,
                correction=f"User requested re-do within {int(elapsed_since_last_sec)}s: '{user_input}'",
                source="implicit",
                weight=1.2,
            )
            return {
                "type": "implicit_correction",
                "lesson_id": lesson_id,
                "topic": topic,
            }

        # 3. Tool Failure Reflection
        if previous_output and any(
            err in previous_output for err in ["Traceback", "Exception:", "Error:", "FAILED", "PermissionError"]
        ):
            # Extract error summary
            error_line = [
                l.strip()
                for l in previous_output.splitlines()
                if any(err in l for err in ["Error", "Exception", "FAILED"])
            ][:1]
            if error_line:
                topic = f"Tool Failure: {error_line[0][:60]}"
                lesson_id = self.lesson_store.add_lesson(
                    topic=topic,
                    correction=f"Avoid triggering error: {error_line[0]}",
                    source="tool_failure",
                    weight=1.5,
                )
                return {
                    "type": "tool_failure_lesson",
                    "lesson_id": lesson_id,
                    "topic": topic,
                }

        return None
