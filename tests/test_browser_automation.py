import pytest
from tools.web_app_tools import gmail_send, gmail_reply, ms365_control
from tools.browser_automation import browser_open_url, browser_click, browser_type


def test_web_app_tool_schemas():
    """Verify tool parameter parsing and argument validation."""
    res_ms = ms365_control({"app": "word"})
    assert isinstance(res_ms, str)

    res_open = browser_open_url({"url": "https://www.google.com", "headless": True})
    assert isinstance(res_open, str)


def test_gmail_tool_definitions():
    """Verify Gmail tool handler exports."""
    assert callable(gmail_send)
    assert callable(gmail_reply)


def test_full_browser_control_tools():
    """Verify schema and handlers for full browser control suite."""
    from tools.browser_automation import (
        browser_new_tab,
        browser_switch_tab,
        browser_scroll,
        browser_eval_js,
        browser_history,
        browser_screenshot,
    )
    assert callable(browser_new_tab)
    assert callable(browser_switch_tab)
    assert callable(browser_scroll)
    assert callable(browser_eval_js)
    assert callable(browser_history)
    assert callable(browser_screenshot)
