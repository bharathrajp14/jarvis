# tests/test_step_planner.py — Unit tests for Conscious Step Planner & Adaptive Step Budget
from __future__ import annotations

import unittest
from agent.step_planner import StepPlanner, AdaptiveStepBudget


class TestStepPlanner(unittest.TestCase):

    def test_step_planner_complexity(self):
        # Complex goal
        res_complex = StepPlanner.plan_steps("build refactor multi-file architecture")
        self.assertEqual(res_complex["complexity"], "HIGH")
        self.assertGreaterEqual(res_complex["initial_budget"], 20)

        # Medium goal
        res_medium = StepPlanner.plan_steps("search web and analyze system status")
        self.assertEqual(res_medium["complexity"], "MEDIUM")
        self.assertEqual(res_medium["initial_budget"], 12)

        # Low goal
        res_low = StepPlanner.plan_steps("hello jarvis")
        self.assertEqual(res_low["complexity"], "LOW")
        self.assertEqual(res_low["initial_budget"], 6)

    def test_adaptive_budget_evaluation(self):
        budget = AdaptiveStepBudget(initial_budget=5, max_ceiling=15)

        # Steps within initial budget
        cont, msg, ext = budget.evaluate(current_step=0, tool_history=[])
        self.assertTrue(cont)
        self.assertFalse(ext)

        cont, msg, ext = budget.evaluate(current_step=4, tool_history=[])
        self.assertTrue(cont)
        self.assertFalse(ext)

        # Step 5 (at limit) with active progress -> should extend +5
        active_history = [
            {"step": 3, "tool_name": "file_read", "result": "Content of file read successfully"},
            {"step": 4, "tool_name": "file_write", "result": "File updated and written successfully"},
        ]
        cont, msg, ext = budget.evaluate(current_step=5, tool_history=active_history)
        self.assertTrue(cont)
        self.assertTrue(ext)
        self.assertEqual(budget.current_budget, 10)

        # Step 10 (at extended limit) with stalled progress -> should stop gracefully
        stalled_history = [
            {"step": 8, "tool_name": "file_read", "result": ""},
            {"step": 9, "tool_name": "file_read", "result": ""},
        ]
        cont, msg, ext = budget.evaluate(current_step=10, tool_history=stalled_history)
        self.assertFalse(cont)
        self.assertFalse(ext)


if __name__ == "__main__":
    unittest.main()
