# core/terminal/events.py — Normalized Input Event Model & Decoder for BR JARVIS MK41
"""
Normalized terminal input event model.
Provides structured abstractions for Mouse, Keyboard, Resize, and Focus events,
with decoders for xterm and SGR (1006) terminal mouse escape sequences.
All coordinates are 0-indexed (x=col, y=row).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class MouseEventType(str, Enum):
    MOUSE_MOVE = "mouse_move"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_TRIPLE_CLICK = "mouse_triple_click"
    MOUSE_DRAG_START = "mouse_drag_start"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_DRAG_END = "mouse_drag_end"
    MOUSE_WHEEL_UP = "mouse_wheel_up"
    MOUSE_WHEEL_DOWN = "mouse_wheel_down"


class MouseButton(str, Enum):
    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"
    WHEEL_UP = "wheel_up"
    WHEEL_DOWN = "wheel_down"
    NONE = "none"


class MouseCaptureMode(str, Enum):
    MOUSE_OFF = "off"
    MOUSE_SCROLL = "scroll"
    MOUSE_INTERACTIVE = "interactive"
    MOUSE_FULL = "full"


@dataclass
class InputEvent:
    """Base class for all normalized terminal input events."""
    timestamp: float = field(default_factory=time.time)
    terminal_source: str = "stdin"


@dataclass
class KeyEvent(InputEvent):
    """Normalized keyboard event."""
    key: str = ""
    char: str = ""
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    meta: bool = False


@dataclass
class MouseEvent(InputEvent):
    """
    Normalized terminal mouse event.
    Coordinates are 0-indexed: x = column (0..cols-1), y = row (0..rows-1).
    """
    event_type: MouseEventType = MouseEventType.MOUSE_MOVE
    x: int = 0
    y: int = 0
    button: MouseButton = MouseButton.NONE
    shift: bool = False
    alt: bool = False
    ctrl: bool = False
    meta: bool = False

    @property
    def is_click(self) -> bool:
        return self.event_type in (
            MouseEventType.MOUSE_CLICK,
            MouseEventType.MOUSE_DOUBLE_CLICK,
            MouseEventType.MOUSE_TRIPLE_CLICK,
        )

    @property
    def is_wheel(self) -> bool:
        return self.event_type in (
            MouseEventType.MOUSE_WHEEL_UP,
            MouseEventType.MOUSE_WHEEL_DOWN,
        )


@dataclass
class ResizeEvent(InputEvent):
    """Terminal window resize event."""
    columns: int = 80
    lines: int = 24


@dataclass
class FocusEvent(InputEvent):
    """Terminal application focus gained/lost event."""
    focused: bool = True


# ── Terminal Mouse Escape Sequence Decoder ───────────────────────────────────

class TerminalInputDecoder:
    """
    Parses raw terminal ANSI escape sequences into normalized InputEvent objects.
    Supports SGR 1006 mouse encoding (\033[<b;x;yM or \033[<b;x;ym)
    and traditional xterm X10/Normal mouse encoding (\033[Mcb cx cy).
    """

    # SGR Extended Mouse Regex: \033[<button;x;y(M|m)
    _SGR_PATTERN = re.compile(r"^\x1b\[<(\d+);(\d+);(\d+)([Mm])")

    def __init__(self, double_click_timeout: float = 0.35):
        self.double_click_timeout = double_click_timeout
        self._last_click_time: float = 0.0
        self._last_click_pos: Tuple[int, int] = (-1, -1)
        self._click_count: int = 0
        self._is_dragging: bool = False

    def decode_sgr_mouse(self, seq: str) -> Optional[Tuple[MouseEvent, int]]:
        """
        Parse SGR 1006 mouse sequence.
        Returns (MouseEvent, consumed_bytes_count) or None.
        """
        match = self._SGR_PATTERN.match(seq)
        if not match:
            return None

        raw_btn = int(match.group(1))
        # SGR sends 1-indexed (col, row); normalize to 0-indexed
        col = int(match.group(2)) - 1
        row = int(match.group(3)) - 1
        action_char = match.group(4)  # 'M' for press/motion, 'm' for release
        consumed_len = match.end()

        is_release = (action_char == "m")

        # Extract modifier bits
        shift = bool(raw_btn & 4)
        alt = bool(raw_btn & 8)
        ctrl = bool(raw_btn & 16)
        is_motion = bool(raw_btn & 32)
        is_wheel = bool(raw_btn & 64)

        base_btn = raw_btn & 3

        now = time.time()

        if is_wheel:
            event_type = MouseEventType.MOUSE_WHEEL_UP if base_btn == 0 else MouseEventType.MOUSE_WHEEL_DOWN
            btn = MouseButton.WHEEL_UP if base_btn == 0 else MouseButton.WHEEL_DOWN
            return MouseEvent(
                event_type=event_type,
                x=col,
                y=row,
                button=btn,
                shift=shift,
                alt=alt,
                ctrl=ctrl,
            ), consumed_len

        if is_motion:
            if base_btn == 0:  # Left drag
                if not self._is_dragging:
                    self._is_dragging = True
                    ev_type = MouseEventType.MOUSE_DRAG_START
                else:
                    ev_type = MouseEventType.MOUSE_DRAG
                btn = MouseButton.LEFT
            else:
                ev_type = MouseEventType.MOUSE_MOVE
                btn = MouseButton.NONE

            return MouseEvent(
                event_type=ev_type,
                x=col,
                y=row,
                button=btn,
                shift=shift,
                alt=alt,
                ctrl=ctrl,
            ), consumed_len

        if is_release:
            if self._is_dragging:
                self._is_dragging = False
                ev_type = MouseEventType.MOUSE_DRAG_END
            else:
                ev_type = MouseEventType.MOUSE_UP
            btn = MouseButton.LEFT if base_btn == 0 else (MouseButton.MIDDLE if base_btn == 1 else MouseButton.RIGHT)
            return MouseEvent(
                event_type=ev_type,
                x=col,
                y=row,
                button=btn,
                shift=shift,
                alt=alt,
                ctrl=ctrl,
            ), consumed_len

        # Button Press -> Determine single, double, or triple click
        btn = MouseButton.LEFT if base_btn == 0 else (MouseButton.MIDDLE if base_btn == 1 else MouseButton.RIGHT)
        if btn == MouseButton.LEFT:
            if (now - self._last_click_time < self.double_click_timeout) and (self._last_click_pos == (col, row)):
                self._click_count += 1
            else:
                self._click_count = 1

            self._last_click_time = now
            self._last_click_pos = (col, row)

            if self._click_count == 2:
                ev_type = MouseEventType.MOUSE_DOUBLE_CLICK
            elif self._click_count >= 3:
                ev_type = MouseEventType.MOUSE_TRIPLE_CLICK
                self._click_count = 0  # Reset
            else:
                ev_type = MouseEventType.MOUSE_CLICK
        else:
            ev_type = MouseEventType.MOUSE_DOWN

        return MouseEvent(
            event_type=ev_type,
            x=col,
            y=row,
            button=btn,
            shift=shift,
            alt=alt,
            ctrl=ctrl,
        ), consumed_len
