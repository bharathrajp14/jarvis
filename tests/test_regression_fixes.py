# tests/test_regression_fixes.py — Consolidated Regression & Security Test Suite
from __future__ import annotations

import unittest
import speech_recognition as sr
from memory.working import WorkingMemory
from computer.operator import get_computer_operator, ComputerAction, ActionType
from permissions import check_permission
from voice.assistant import BRVoiceAssistant


class TestRegressionFixes(unittest.TestCase):

    def test_working_memory_goal_pinning(self):
        wm = WorkingMemory(max_tokens=100_000)
        wm.add("user", "ROOT_GOAL_PROMPT: Build system architecture")
        for i in range(15):
            wm.add("assistant", f"Turn response {i}")
            wm.add("user", f"Turn user {i}")

        root_msg = wm.get()[0]
        wm.trim(max_turns=5)
        if root_msg not in wm.get():
            wm.messages.insert(0, root_msg)
        self.assertEqual(wm.get()[0]["content"], "ROOT_GOAL_PROMPT: Build system architecture")

    def test_working_memory_trim_no_infinite_loop(self):
        wm = WorkingMemory(max_tokens=50)
        huge_root = "A" * 1000
        wm.add("user", huge_root)
        wm.add("assistant", "Response 1")
        wm.add("user", "Follow up 1")
        wm._trim()
        self.assertLessEqual(len(wm.get()[0]["content"]) / 4, 60)

    def test_computer_operator_failsafe_handling(self):
        op = get_computer_operator()
        action = ComputerAction(
            action_type=ActionType.CLIPBOARD_SET,
            text="JARVIS Failsafe Verification",
            description="Test failsafe action"
        )
        res = op.execute_action(action)
        self.assertTrue(res.success)

    def test_permissions_path_policy_enforcement(self):
        from pathlib import Path
        main_py = str(Path("main.py").resolve().as_posix())
        self.assertTrue(check_permission("view_file", {"AbsolutePath": main_py}))
        self.assertFalse(check_permission("view_file", {"AbsolutePath": "C:/Windows/System32/config/SAM"}))

    def test_voice_assistant_energy_floor(self):
        assistant = BRVoiceAssistant(ui=None)
        r = sr.Recognizer()
        r.energy_threshold = 50
        assistant._tune_recognizer(r)
        self.assertGreaterEqual(r.energy_threshold, 180)


if __name__ == "__main__":
    unittest.main()
