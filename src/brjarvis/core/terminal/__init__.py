# core/terminal/__init__.py — Master Terminal Agent Package for BR JARVIS
from __future__ import annotations

from typing import Optional

import sys
if __name__ in sys.modules:
    sys.modules.setdefault("core.terminal", sys.modules[__name__])

from ..runtime import ApplicationRuntime
from .actions import ActionRegistry, FocusManager, FocusState
from .commands import SlashCommandHandler, VALID_MODES
from .components import (
    CollapsibleOutputComponent,
    HeaderComponent,
    PermissionPromptComponent,
    PlanViewComponent,
    StatusPanelComponent,
    ToolCallComponent,
)
from .events import (
    FocusEvent,
    InputEvent,
    KeyEvent,
    MouseButton,
    MouseCaptureMode,
    MouseEvent,
    MouseEventType,
    ResizeEvent,
    TerminalInputDecoder,
)
from .guard import TerminalStateGuard
from .hit_test import HitTestManager, InteractiveRegion, RegionType
from .interactive_tui import InteractiveTUIController
from .renderer import TerminalRenderer
from .selection import (
    ClipboardProvider,
    SelectionManager,
    SelectionMode,
    SelectionRange,
)
from .session import TerminalSession
from .theme import Glyphs, MODE_COLORS, get_terminal_theme
from .viewport import ScrollManager, ViewportRange


def run_cli(
    runtime: Optional[ApplicationRuntime] = None,
    mode: str = "general",
    session_id: Optional[str] = None,
) -> None:
    """Launch the interactive BR JARVIS CLI Agent REPL."""
    session = TerminalSession(runtime=runtime, mode=mode, session_id=session_id)
    session.run_repl()


def run_query(
    query: str,
    runtime: Optional[ApplicationRuntime] = None,
    mode: str = "general",
) -> int:
    """Execute a one-shot query using the BR JARVIS terminal agent."""
    session = TerminalSession(runtime=runtime, mode=mode, auto_welcome=False)
    return session.run_query(query)


__all__ = [
    "TerminalSession",
    "TerminalRenderer",
    "SlashCommandHandler",
    "TerminalStateGuard",
    "InteractiveTUIController",
    "HitTestManager",
    "InteractiveRegion",
    "RegionType",
    "SelectionManager",
    "SelectionRange",
    "SelectionMode",
    "ClipboardProvider",
    "ScrollManager",
    "ViewportRange",
    "ActionRegistry",
    "FocusManager",
    "FocusState",
    "InputEvent",
    "KeyEvent",
    "MouseEvent",
    "MouseEventType",
    "MouseButton",
    "MouseCaptureMode",
    "ResizeEvent",
    "TerminalInputDecoder",
    "HeaderComponent",
    "ToolCallComponent",
    "CollapsibleOutputComponent",
    "PermissionPromptComponent",
    "PlanViewComponent",
    "StatusPanelComponent",
    "Glyphs",
    "MODE_COLORS",
    "VALID_MODES",
    "get_terminal_theme",
    "run_cli",
    "run_query",
]
