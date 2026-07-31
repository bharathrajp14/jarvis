# tests/test_flaw_remediations_v5.py — Unit tests for PyAutoGUI failsafe & file watcher remediations
from __future__ import annotations

import unittest
from computer.operator import get_computer_operator, ComputerAction, ActionType
from watchers.file_watcher import FileWatcher


class TestFlawRemediationsV5(unittest.TestCase):

    def test_computer_operator_failsafe_handling(self):
        op = get_computer_operator()
        action = ComputerAction(
            action_type=ActionType.CLIPBOARD_SET,
            text="JARVIS Failsafe Verification",
            description="Test failsafe action"
        )
        res = op.execute_action(action)
        self.assertTrue(res.success)

    def test_file_watcher_scan_safety(self):
        fw = FileWatcher(watch_path=".")
        changes = fw.scan_for_changes()
        self.assertIsInstance(changes, int)


if __name__ == "__main__":
    unittest.main()
