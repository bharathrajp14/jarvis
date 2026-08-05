# tests/test_computer_operator.py — Unit Tests for Priority 10 Computer Operator
from __future__ import annotations

import pytest
from computer.operator import ComputerOperator, get_computer_operator
from computer.types import ActionResult, ActionType, ComputerAction


def test_computer_operator_execution():
    operator = get_computer_operator()

    # Clipboard set action
    action = ComputerAction(
        action_type=ActionType.CLIPBOARD_SET,
        text="Test Clipboard Data",
        description="Copying test data to clipboard",
    )
    res = operator.execute_action(action)

    assert isinstance(res, ActionResult)
    assert res.success is True

    # Clipboard get action
    get_action = ComputerAction(
        action_type=ActionType.CLIPBOARD_GET,
        description="Reading test data from clipboard",
    )
    get_res = operator.execute_action(get_action)

    assert get_res.success is True
    assert get_res.data == "Test Clipboard Data"
