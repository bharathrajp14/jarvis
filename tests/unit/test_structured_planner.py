# tests/unit/test_structured_planner.py — Unit Tests for Structured Plan Validation
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from agent.planner import _fallback_plan, _validate_and_sanitize_plan, create_plan, replan
from gateway.client import ModelResponse


class TestStructuredPlanner(unittest.TestCase):

    def test_validate_valid_plan(self):
        raw = {
            "goal": "Build website",
            "can_parallelize": True,
            "steps": [
                {
                    "step": 1,
                    "tool": "file_controller",
                    "description": "Create index.html",
                    "parameters": {"action": "write", "path": "index.html"},
                    "depends_on": [],
                    "parallel": True,
                    "critical": True
                }
            ]
        }
        sanitized = _validate_and_sanitize_plan(raw, "Build website")
        self.assertEqual(len(sanitized["steps"]), 1)
        self.assertEqual(sanitized["steps"][0]["tool"], "file_controller")
        self.assertTrue(sanitized["can_parallelize"])

    def test_safety_transform_generated_code_to_search(self):
        raw = {
            "goal": "Find info",
            "steps": [
                {
                    "step": 1,
                    "tool": "generated_code",
                    "description": "Run arbitrary script",
                    "parameters": {"code": "print(1)"}
                }
            ]
        }
        sanitized = _validate_and_sanitize_plan(raw, "Find info")
        self.assertEqual(sanitized["steps"][0]["tool"], "web_search")

    def test_fallback_plan_generation(self):
        plan = _fallback_plan("search for latest Python release")
        self.assertEqual(plan["steps"][0]["tool"], "web_search")
        self.assertIn("Python", plan["steps"][0]["parameters"]["query"])

    @patch("gateway.execution.ModelExecutionService.execute")
    def test_create_plan_with_mocked_llm(self, mock_execute):
        mock_execute.return_value = ModelResponse(
            text='{"goal": "Search query", "steps": [{"step": 1, "tool": "web_search", "description": "Search web", "parameters": {"query": "AI"}}]}'
        )
        plan = create_plan("Search for AI")
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["tool"], "web_search")


if __name__ == "__main__":
    unittest.main()
