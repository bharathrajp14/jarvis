# tests/test_flaw_remediations_v5.py — Unit tests for PyAutoGUI failsafe & file watcher remediations
from __future__ import annotations

import unittest
from computer.operator import ComputerOperator, ComputerAction, ActionType
from watchers.file_watcher import FileWatcher


class TestFlawRemediationsV5(unittest.TestCase):

    def test_computer_operator_failsafe_handling(self):
        op = ComputerOperator()
        action = ComputerAction(
            action_type=ActionType.MOUSE_CLICK,
            x=10, y=10,
            description="Test click action"
        )
        res = op.execute_action(action)
        self.assertTrue(res.success)
        self.assertIn("Verified", res.verification_message)

    def test_file_watcher_scan_safety(self):
        fw = FileWatcher(observed_paths=["."])
        changes = fw.scan_for_changes()
        self.assertIsInstance(changes, int)


if __name__ == "__main__":
    unittest.main()
