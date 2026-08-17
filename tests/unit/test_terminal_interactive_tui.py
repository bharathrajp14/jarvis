# tests/unit/test_terminal_interactive_tui.py — Unit Tests for Interactive TUI Controller
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from rich.console import Console

from brjarvis.core.terminal.events import (
    MouseButton,
    MouseCaptureMode,
    MouseEvent,
    MouseEventType,
)
from brjarvis.core.terminal.interactive_tui import InteractiveTUIController
from brjarvis.security.permission_request import PermissionRequest, RiskLevel


class TestInteractiveTUI:
    """Test suite for InteractiveTUIController mouse handling and component regions."""

    def test_wheel_event_triggers_scroll(self):
        tui = InteractiveTUIController(mouse_mode=MouseCaptureMode.MOUSE_INTERACTIVE)
        tui.scroll.update_dimensions(content_height=100, viewport_height=20)
        assert tui.scroll.scroll_offset == 80

        # Wheel Up
        ev_up = MouseEvent(
            event_type=MouseEventType.MOUSE_WHEEL_UP,
            x=10,
            y=10,
            button=MouseButton.WHEEL_UP,
        )
        handled = tui.handle_mouse_event(ev_up)
        assert handled is True
        assert tui.scroll.scroll_offset < 80

    def test_collapsible_tool_rendering_and_toggle(self):
        tui = InteractiveTUIController()
        content = "\n".join(f"Output line {i}" for i in range(15))

        # Initial render -> collapsed
        rendered = tui.render_interactive_tool_result(
            tool_id="shell_1",
            tool_name="shell",
            content=content,
            max_lines=4,
            start_y=2,
        )
        assert any("hidden" in line for line in rendered)

        # Region was registered at collapse row (start_y=2 + header + 2 preview lines = 5)
        reg = tui.hit_test.hit_test(6, 5)
        assert reg is not None
        assert reg.action_name == "tool:toggle"
        assert reg.action_args == {"tool_id": "shell_1"}

        # Simulate click on region
        ev_click = MouseEvent(
            event_type=MouseEventType.MOUSE_CLICK,
            x=6,
            y=5,
            button=MouseButton.LEFT,
        )
        tui.handle_mouse_event(ev_click)
        assert "shell_1" in tui.expanded_tools

    def test_interactive_permission_prompt_dispatch(self):
        tui = InteractiveTUIController()
        req = PermissionRequest(
            tool="file_delete",
            target="test.txt",
            risk_level=RiskLevel.CRITICAL,
        )
        callback_mock = MagicMock()

        rendered = tui.render_interactive_permission_prompt(
            request_obj=req,
            start_y=0,
            callback=callback_mock,
        )
        assert len(rendered) >= 5

        # Hit test on 'allow_once' button row (row 5)
        reg = tui.hit_test.hit_test(6, 5)
        assert reg is not None
        assert reg.action_name == "permission:select"
        assert reg.action_args == {"decision": "allow_once"}

        # Click event on button
        ev_click = MouseEvent(
            event_type=MouseEventType.MOUSE_CLICK,
            x=6,
            y=5,
            button=MouseButton.LEFT,
        )
        tui.handle_mouse_event(ev_click)
        callback_mock.assert_called_once_with("allow_once")
