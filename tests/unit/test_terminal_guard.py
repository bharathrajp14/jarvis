# tests/unit/test_terminal_guard.py — Unit Tests for Terminal State Guard
from __future__ import annotations

from unittest.mock import patch

from brjarvis.core.terminal.guard import (
    MouseCaptureMode,
    TerminalStateGuard,
)


class TestTerminalGuard:
    """Test suite for TerminalStateGuard and emergency cleanup handlers."""

    def test_singleton_instance(self):
        g1 = TerminalStateGuard.get_instance()
        g2 = TerminalStateGuard.get_instance()
        assert g1 is g2

    def test_state_transitions(self):
        guard = TerminalStateGuard()
        with patch.object(guard, "_write_raw") as mock_write:
            guard.enter_alternate_screen()
            assert guard.is_alt_screen is True
            mock_write.assert_called()

            guard.hide_cursor()
            assert guard.is_cursor_hidden is True

            guard.enable_mouse_capture(MouseCaptureMode.MOUSE_INTERACTIVE)
            assert guard.is_mouse_active is True
            assert guard.mouse_mode == MouseCaptureMode.MOUSE_INTERACTIVE

            # Restore
            guard.restore_all()
            assert guard.is_alt_screen is False
            assert guard.is_cursor_hidden is False
            assert guard.is_mouse_active is False

    def test_suspend_for_external_context_manager(self):
        guard = TerminalStateGuard()
        with patch.object(guard, "_write_raw"):
            guard.enter_alternate_screen()
            guard.enable_mouse_capture(MouseCaptureMode.MOUSE_FULL)

            assert guard.is_alt_screen is True
            assert guard.is_mouse_active is True

            with guard.suspend_for_external():
                # Inside context manager, state is restored to standard terminal
                assert guard.is_alt_screen is False
                assert guard.is_mouse_active is False

            # Upon exiting context manager, state is restored back to TUI
            assert guard.is_alt_screen is True
            assert guard.is_mouse_active is True
