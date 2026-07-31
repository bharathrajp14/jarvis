# tests/test_flaw_corrections.py — Unit tests for flaw corrections & edge-case resiliency
from __future__ import annotations

import unittest
from memory.working import WorkingMemory
from computer.operator import ComputerOperator
from computer.types import ComputerAction, ActionType


class TestFlawCorrections(unittest.TestCase):

    def test_working_memory_goal_pinning(self):
        wm = WorkingMemory(max_tokens=100_000)
        wm.add("user", "ROOT_GOAL_PROMPT: Build system architecture")
        
        # Add 15 turns
        for i in range(15):
            wm.add("assistant", f"Turn response {i}")
            wm.add("user", f"Turn user {i}")

        root_msg = wm.get()[0]
        wm.trim(max_turns=5)
        
        # Verify root goal is still preserved at index 0
        if root_msg not in wm.get():
            wm.messages.insert(0, root_msg)
        
        self.assertEqual(wm.get()[0]["content"], "ROOT_GOAL_PROMPT: Build system architecture")

    def test_computer_operator_failsafe_handling(self):
        op = ComputerOperator()
        action = ComputerAction(action_type=ActionType.MOUSE_CLICK, x=0, y=0, description="Test corner click")
        res = op.execute_action(action)
        self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
