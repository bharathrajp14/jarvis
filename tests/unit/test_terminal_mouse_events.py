# tests/unit/test_terminal_mouse_events.py — Unit Tests for Terminal Mouse Event Decoders
from __future__ import annotations

import pytest
from brjarvis.core.terminal.events import (
    MouseButton,
    MouseCaptureMode,
    MouseEvent,
    MouseEventType,
    TerminalInputDecoder,
)


class TestTerminalMouseEvents:
    """Test suite for SGR 1006 mouse protocol parsing and normalized event model."""

    def test_mouse_event_properties(self):
        ev = MouseEvent(
            event_type=MouseEventType.MOUSE_CLICK,
            x=10,
            y=5,
            button=MouseButton.LEFT,
        )
        assert ev.x == 10
        assert ev.y == 5
        assert ev.is_click is True
        assert ev.is_wheel is False

        wheel_ev = MouseEvent(
            event_type=MouseEventType.MOUSE_WHEEL_UP,
            x=0,
            y=0,
            button=MouseButton.WHEEL_UP,
        )
        assert wheel_ev.is_wheel is True
        assert wheel_ev.is_click is False

    def test_decode_sgr_left_click(self):
        decoder = TerminalInputDecoder()
        # SGR sequence: \x1b[<0;15;6M (Button 0 = left press, col 15, row 6)
        raw = "\x1b[<0;15;6M"
        res = decoder.decode_sgr_mouse(raw)
        assert res is not None
        ev, consumed = res
        assert consumed == len(raw)
        assert ev.event_type == MouseEventType.MOUSE_CLICK
        # 1-indexed to 0-indexed normalization
        assert ev.x == 14
        assert ev.y == 5
        assert ev.button == MouseButton.LEFT

    def test_decode_sgr_wheel_events(self):
        decoder = TerminalInputDecoder()
        # Wheel Up: raw_btn = 64 (bit 6 set) -> \x1b[<64;20;10M
        raw_up = "\x1b[<64;20;10M"
        res_up = decoder.decode_sgr_mouse(raw_up)
        assert res_up is not None
        ev_up, _ = res_up
        assert ev_up.event_type == MouseEventType.MOUSE_WHEEL_UP
        assert ev_up.button == MouseButton.WHEEL_UP
        assert ev_up.x == 19
        assert ev_up.y == 9

        # Wheel Down: raw_btn = 65 -> \x1b[<65;20;10M
        raw_down = "\x1b[<65;20;10M"
        res_down = decoder.decode_sgr_mouse(raw_down)
        assert res_down is not None
        ev_down, _ = res_down
        assert ev_down.event_type == MouseEventType.MOUSE_WHEEL_DOWN
        assert ev_down.button == MouseButton.WHEEL_DOWN

    def test_decode_sgr_modifiers(self):
        decoder = TerminalInputDecoder()
        # Shift + Left Click: button = 0 + 4 (shift) = 4 -> \x1b[<4;10;10M
        raw = "\x1b[<4;10;10M"
        res = decoder.decode_sgr_mouse(raw)
        assert res is not None
        ev, _ = res
        assert ev.shift is True
        assert ev.ctrl is False

    def test_decode_drag_motion(self):
        decoder = TerminalInputDecoder()
        # Motion with button 0 pressed: button = 32 -> \x1b[<32;12;8M
        raw_drag = "\x1b[<32;12;8M"
        res = decoder.decode_sgr_mouse(raw_drag)
        assert res is not None
        ev, _ = res
        assert ev.event_type == MouseEventType.MOUSE_DRAG_START
        assert ev.button == MouseButton.LEFT

        # Follow-up motion
        raw_drag2 = "\x1b[<32;13;8M"
        res2 = decoder.decode_sgr_mouse(raw_drag2)
        assert res2 is not None
        ev2, _ = res2
        assert ev2.event_type == MouseEventType.MOUSE_DRAG
