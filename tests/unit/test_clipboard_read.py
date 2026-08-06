# tests/test_clipboard_read.py — Unit tests for system clipboard reading & tool integration
from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock
from actions.clipboard_utils import get_clipboard_text, set_clipboard_text
from tools.pc_tools import tool_clipboard_read
from actions.computer_control import computer_control
from computer.operator import get_computer_operator
from computer.types import ActionType, ComputerAction


class TestClipboardUtils(unittest.TestCase):

    def test_clipboard_set_get_roundtrip(self):
        test_str = "JARVIS_UNIT_TEST_CLIPBOARD_STRING_12345"
        success = set_clipboard_text(test_str)
        self.assertTrue(success)
        retrieved = get_clipboard_text()
        self.assertEqual(retrieved, test_str)

    def test_pyperclip_failure_fallback(self):
        test_str = "JARVIS_FALLBACK_TEST_STRING_67890"
        set_clipboard_text(test_str)
        
        # Mock pyperclip.paste to throw exception
        with patch("pyperclip.paste", side_effect=Exception("pyperclip error")):
            retrieved = get_clipboard_text()
            self.assertEqual(retrieved, test_str)

    def test_tool_clipboard_read(self):
        test_str = "TOOL_READ_CLIPBOARD_DATA"
        with patch("pyperclip.paste", return_value=test_str):
            result = tool_clipboard_read({})
            self.assertEqual(result, test_str)

    def test_computer_control_clipboard_get(self):
        test_str = "COMPUTER_CONTROL_GET_DATA"
        with patch("pyperclip.paste", return_value=test_str):
            result = computer_control(parameters={"action": "clipboard_get"})
            self.assertEqual(result, test_str)


    def test_computer_operator_clipboard(self):
        operator = get_computer_operator()
        test_str = "COMPUTER_OPERATOR_CLIPBOARD_DATA"

        set_action = ComputerAction(
            action_type=ActionType.CLIPBOARD_SET,
            text=test_str,
            description="Testing clipboard set",
        )
        set_res = operator.execute_action(set_action)
        self.assertTrue(set_res.success)

        get_action = ComputerAction(
            action_type=ActionType.CLIPBOARD_GET,
            description="Testing clipboard get",
        )
        get_res = operator.execute_action(get_action)
        self.assertTrue(get_res.success)
        self.assertEqual(get_res.data, test_str)


if __name__ == "__main__":
    unittest.main()
