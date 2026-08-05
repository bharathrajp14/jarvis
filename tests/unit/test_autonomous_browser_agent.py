# tests/test_autonomous_browser_agent.py — Tests for Autonomous Web Task Execution Subsystem
import pytest
from tools.autonomous_browser_agent import (
    browser_execute_web_task,
    browser_auto_navigate_and_extract,
    browser_fill_and_submit_form,
)


def test_autonomous_browser_tools_importable():
    """Verify tool functions are importable and callable."""
    assert callable(browser_execute_web_task)
    assert callable(browser_auto_navigate_and_extract)
    assert callable(browser_fill_and_submit_form)
