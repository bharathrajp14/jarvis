# core/terminal/interactive_tui.py — Fullscreen Interactive TUI Controller for BR JARVIS MK41
"""
Fullscreen Interactive TUI Subsystem for BR JARVIS.
Integrates virtualized viewport scrolling, spatial hit-testing, selection & clipboard,
interactive permission choices, collapsible tool results, and terminal state guards.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console

from .actions import ActionRegistry, FocusManager
from .events import (
    MouseCaptureMode,
    MouseEvent,
    MouseEventType,
    TerminalInputDecoder,
)
from .guard import TerminalStateGuard
from .hit_test import HitTestManager, RegionType
from .selection import SelectionManager, SelectionMode
from .theme import (
    COLOR_AMBER,
    COLOR_GREEN,
    COLOR_RED,
    Glyphs,
)
from .viewport import ScrollManager

logger = logging.getLogger("JARVIS.InteractiveTUI")


class InteractiveTUIController:
    """
    Master Interactive TUI Controller for BR JARVIS.
    Combines mouse hit-testing, virtualized scrolling, expandable tool results,
    clickable links & paths, interactive permission dialogs, and text selection.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        mouse_mode: MouseCaptureMode = MouseCaptureMode.MOUSE_INTERACTIVE,
    ):
        self.console: Console = console or Console(highlight=False)
        self.guard: TerminalStateGuard = TerminalStateGuard.get_instance()
        self.decoder: TerminalInputDecoder = TerminalInputDecoder()
        self.hit_test: HitTestManager = HitTestManager()
        self.selection: SelectionManager = SelectionManager()
        self.scroll: ScrollManager = ScrollManager()
        self.focus: FocusManager = FocusManager()
        self.actions: ActionRegistry = ActionRegistry()

        self.mouse_mode: MouseCaptureMode = mouse_mode
        self.expanded_tools: set[str] = set()
        self.raw_transcript_lines: List[str] = []
        self._permission_callback: Optional[Callable[[str], None]] = None
        self._pending_permission_req: Optional[Any] = None

        self._setup_action_handlers()

    def _setup_action_handlers(self) -> None:
        """Register default action handlers for TUI interactions."""
        self.actions.register("tool:toggle", self._on_tool_toggle)
        self.actions.register("scroll:lineUp", lambda args: self.scroll.scroll_up(args.get("lines", 1)))
        self.actions.register("scroll:lineDown", lambda args: self.scroll.scroll_down(args.get("lines", 1)))
        self.actions.register("scroll:pageUp", lambda args: self.scroll.scroll_page_up())
        self.actions.register("scroll:pageDown", lambda args: self.scroll.scroll_page_down())
        self.actions.register("scroll:bottom", lambda args: self.scroll.scroll_to_bottom())
        self.actions.register("permission:select", self._on_permission_select)

    def _on_tool_toggle(self, args: Dict[str, Any]) -> None:
        """Toggle expanded/collapsed state of a tool result."""
        tool_id = str(args.get("tool_id", ""))
        if tool_id:
            if tool_id in self.expanded_tools:
                self.expanded_tools.remove(tool_id)
            else:
                self.expanded_tools.add(tool_id)

    def _on_permission_select(self, args: Dict[str, Any]) -> None:
        """Handle click on permission decision option."""
        decision = str(args.get("decision", "deny"))
        if self._permission_callback:
            cb = self._permission_callback
            self._permission_callback = None
            self._pending_permission_req = None
            cb(decision)

    # ── Mouse & Keyboard Event Dispatch ───────────────────────────────────────

    def handle_mouse_event(self, event: MouseEvent) -> bool:
        """
        Process a normalized mouse event.
        Dispatches clicks to interactive regions, selection drags, or viewport scroll.
        Returns True if event was handled.
        """
        if self.mouse_mode == MouseCaptureMode.MOUSE_OFF:
            return False

        # 1. Wheel Scrolling
        if event.is_wheel:
            if event.event_type == MouseEventType.MOUSE_WHEEL_UP:
                self.scroll.scroll_up(self.scroll.scroll_speed)
                return True
            elif event.event_type == MouseEventType.MOUSE_WHEEL_DOWN:
                self.scroll.scroll_down(self.scroll.scroll_speed)
                return True

        # If scroll-only mode, ignore clicks
        if self.mouse_mode == MouseCaptureMode.MOUSE_SCROLL:
            return False

        # 2. Hover Update
        if event.event_type == MouseEventType.MOUSE_MOVE:
            _, changed = self.hit_test.update_hover(event.x, event.y)
            return changed

        # 3. Single / Double / Triple Click Dispatch
        if event.event_type in (
            MouseEventType.MOUSE_CLICK,
            MouseEventType.MOUSE_DOUBLE_CLICK,
            MouseEventType.MOUSE_TRIPLE_CLICK,
        ):
            target = self.hit_test.hit_test(event.x, event.y)
            if target and target.action_name:
                self.actions.execute(target.action_name, target.action_args)
                return True

            # If no interactive region was clicked, perform transcript text selection
            if event.event_type == MouseEventType.MOUSE_DOUBLE_CLICK:
                if 0 <= event.y < len(self.raw_transcript_lines):
                    line = self.raw_transcript_lines[event.y]
                    self.selection.select_word_at(line, event.y, event.x)
                    return True
            elif event.event_type == MouseEventType.MOUSE_TRIPLE_CLICK:
                if 0 <= event.y < len(self.raw_transcript_lines):
                    line = self.raw_transcript_lines[event.y]
                    self.selection.select_line_at(line, event.y)
                    return True

            self.selection.clear()
            return False

        # 4. Mouse Drag Selection
        if event.event_type == MouseEventType.MOUSE_DRAG_START:
            self.selection.start_selection(row=event.y, col=event.x, mode=SelectionMode.CHAR)
            return True
        elif event.event_type == MouseEventType.MOUSE_DRAG:
            self.selection.update_selection(row=event.y, col=event.x)
            return True
        elif event.event_type == MouseEventType.MOUSE_DRAG_END:
            self.selection.end_selection(lines=self.raw_transcript_lines)
            return True

        return False

    # ── Interactive Region Rendering ──────────────────────────────────────────

    def render_interactive_tool_result(
        self,
        tool_id: str,
        tool_name: str,
        content: str,
        verified: bool = True,
        start_y: int = 0,
        max_lines: int = 5,
    ) -> List[str]:
        """
        Render a collapsible tool result card and register its clickable region.
        """
        is_expanded = tool_id in self.expanded_tools
        lines = content.strip().split("\n")
        rendered_output: List[str] = []

        status_glyph = Glyphs.CHECK if verified else Glyphs.WARNING
        color = COLOR_GREEN if verified else COLOR_AMBER

        header = f"  [{color}]{status_glyph} {tool_name}[/{color}]"
        rendered_output.append(header)

        if not is_expanded and len(lines) > max_lines:
            # Render first few lines + collapsed banner
            for line in lines[:2]:
                rendered_output.append(f"    [dim]{line}[/dim]")

            hidden_count = len(lines) - 2
            collapse_row = start_y + len(rendered_output)
            banner = f"    [cyan bold]▶ [{hidden_count} lines hidden — click to expand][/cyan bold]"
            rendered_output.append(banner)

            # Register clickable region for expansion
            self.hit_test.register(
                region_id=f"tool_collapse_{tool_id}",
                region_type=RegionType.TOOL_RESULT,
                x=4,
                y=collapse_row,
                width=len(banner) - 15,
                height=1,
                action="tool:toggle",
                args={"tool_id": tool_id},
                tooltip="Click to expand/collapse tool output",
            )
        else:
            for line in lines:
                rendered_output.append(f"    {line}")

            if len(lines) > max_lines:
                collapse_row = start_y + len(rendered_output)
                banner = "    [cyan bold]▼ [click to collapse][/cyan bold]"
                rendered_output.append(banner)

                self.hit_test.register(
                    region_id=f"tool_collapse_{tool_id}",
                    region_type=RegionType.TOOL_RESULT,
                    x=4,
                    y=collapse_row,
                    width=25,
                    height=1,
                    action="tool:toggle",
                    args={"tool_id": tool_id},
                    tooltip="Click to collapse tool output",
                )

        return rendered_output

    def render_interactive_permission_prompt(
        self,
        request_obj: Any,
        start_y: int = 0,
        callback: Optional[Callable[[str], None]] = None,
    ) -> List[str]:
        """
        Render an interactive permission card with whole-row clickable choices.
        """
        self._permission_callback = callback
        self._pending_permission_req = request_obj

        tool = getattr(request_obj, "tool", "action")
        target = getattr(request_obj, "target", "")
        risk = getattr(request_obj, "risk_level", "HIGH")
        risk_str = risk.value if hasattr(risk, "value") else str(risk)

        output: List[str] = [
            f"[bold {COLOR_AMBER}]⚠ Permission Required for {tool}[/]",
            f"  [dim]Target:[/] {target}",
            f"  [dim]Risk Level:[/] [bold {COLOR_RED}]{risk_str.upper()}[/]",
            "",
            "  Options (click or press key):",
        ]

        options = [
            ("[y] Allow Once", "allow_once"),
            ("[s] Allow for Session", "allow_session"),
            ("[t] Allow this Tool", "allow_tool"),
            ("[n] Deny Action", "deny"),
            ("[c] Cancel Turn", "cancel"),
        ]

        for label, decision in options:
            row_y = start_y + len(output)
            opt_line = f"    • [bold cyan]{label}[/bold cyan]"
            output.append(opt_line)

            # Whole-row clickable hit region
            self.hit_test.register(
                region_id=f"perm_opt_{decision}",
                region_type=RegionType.BUTTON,
                x=4,
                y=row_y,
                width=40,
                height=1,
                action="permission:select",
                args={"decision": decision},
                priority=20,
            )

        return output
