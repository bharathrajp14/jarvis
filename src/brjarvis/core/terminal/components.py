# core/terminal/components.py — Modular Terminal UI Component System
"""
Reusable rich terminal UI components for BR JARVIS agent terminal.
Provides consistent visual semantics, collapsible outputs, glyph-based progress,
and interactive prompts.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from .theme import (
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_BORDER,
    COLOR_CYAN,
    COLOR_DARK,
    COLOR_DIM,
    COLOR_GREEN,
    COLOR_MAGENTA,
    COLOR_MUTED,
    COLOR_ORANGE,
    COLOR_PANEL_BG,
    COLOR_PURPLE,
    COLOR_RED,
    COLOR_TEAL,
    COLOR_WHITE,
    Glyphs,
    MODE_COLORS,
)
from ..version import CODENAME, VERSION

try:
    from rich.box import DOUBLE, HEAVY, ROUNDED, SIMPLE
    from rich.console import Console, Group, RenderableType
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class HeaderComponent:
    """Renders a clean, compact session header status bar."""

    @staticmethod
    def render(
        console: Optional[Console],
        session_id: str,
        mode: str = "general",
        model: str = "Gemini 2.5 Flash",
        permission_mode: str = "confirm_destructive",
        working_dir: str = "",
    ) -> None:
        if not HAS_RICH or not console:
            print(f"[⚡ BR JARVIS v{VERSION} | Mode: {mode.upper()} | Model: {model} | ID: {session_id[:8]} | Perms: {permission_mode}]")
            return

        mode_color = MODE_COLORS.get(mode.lower(), COLOR_CYAN)
        short_id = session_id[:8]
        dir_name = os.path.basename(working_dir) if working_dir else "workspace"

        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)

        left = Text()
        left.append(f"{Glyphs.LIGHTNING} BR JARVIS ", style="bold cyan")
        left.append(f"v{VERSION} ", style="bold white")
        left.append(f"[{CODENAME}] ", style="dim")
        left.append("│ Mode: ", style="dim")
        left.append(f"{mode.upper()} ", style=f"bold {mode_color}")
        left.append("│ Model: ", style="dim")
        left.append(f"{model} ", style="bold cyan")

        right = Text()
        right.append("Session: ", style="dim")
        right.append(f"{short_id} ", style="white")
        right.append("│ Dir: ", style="dim")
        right.append(f"📁 {dir_name} ", style="cyan")
        right.append("│ Shield: ", style="dim")
        right.append(f"{Glyphs.SHIELD} {permission_mode.upper()}", style="bold green")

        grid.add_row(left, right)
        panel = Panel(
            grid,
            box=ROUNDED,
            border_style=COLOR_CYAN,
            padding=(0, 1),
        )
        console.print(panel)


class WelcomeCard:
    """Renders a visually stunning welcome banner with quick-action shortcuts."""

    @staticmethod
    def render(
        console: Optional[Console],
        mode: str = "general",
        working_dir: str = "",
        model_name: str = "Gemini",
    ) -> None:
        if not HAS_RICH or not console:
            print("==================================================================")
            print(f"⚡ BR JARVIS v{VERSION} ({CODENAME}) — Autonomous Agent Terminal")
            print("  Commands: /help, /mode <name>, /plan, /tasks, /doctor, /quit")
            print("==================================================================")
            return

        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=3)
        grid.add_column(ratio=2)

        # Left column: Description and quick prompts
        left = Text()
        left.append(f"{Glyphs.LIGHTNING} BR JARVIS MK40.2+ ", style="bold cyan")
        left.append(f"v{VERSION} ", style="bold white")
        left.append(f"({CODENAME})\n", style="dim")
        left.append("Autonomous Cognitive Agent Terminal with Multimodal Reasoning & Tool Lifecycle.\n\n", style="white")

        left.append("Quick Commands:\n", style="bold cyan")
        left.append("  /plan <goal>     ", style="bold teal")
        left.append("Generate multi-stage execution plan for review\n", style="dim")
        left.append("  /mode <name>     ", style="bold teal")
        left.append("Switch persona: coder, analyst, recon, planner, general\n", style="dim")
        left.append("  /mouse [mode]    ", style="bold teal")
        left.append("Configure terminal mouse: on, off, scroll, interactive\n", style="dim")
        left.append("  /doctor          ", style="bold teal")
        left.append("Run self-healing diagnostics and verify system integrity\n", style="dim")
        left.append("  /help            ", style="bold teal")
        left.append("Show command reference, keybindings, and workflows\n", style="dim")

        # Right column: Context badge panel
        right = Table.grid(expand=True)
        right.add_column(ratio=1)

        t_ctx = Text()
        t_ctx.append("Active Workspace:\n", style="bold white")
        t_ctx.append(f"  📁 {os.path.basename(working_dir) or 'BrJarvis'}\n", style="bold cyan")
        t_ctx.append(f"  [dim]{working_dir or os.getcwd()}[/dim]\n\n")

        t_ctx.append("Keyboard Shortcuts:\n", style="bold white")
        t_ctx.append("  [Tab]       ", style="bold green")
        t_ctx.append("Autocomplete commands\n", style="dim")
        t_ctx.append("  [/]         ", style="bold green")
        t_ctx.append("Open command menu\n", style="dim")
        t_ctx.append("  [Ctrl+C]    ", style="bold yellow")
        t_ctx.append("Interrupt active task\n", style="dim")
        t_ctx.append("  [Ctrl+D]    ", style="bold red")
        t_ctx.append("Exit session cleanly\n", style="dim")

        right.add_row(t_ctx)

        grid.add_row(left, right)

        panel = Panel(
            grid,
            border_style=COLOR_CYAN,
            box=ROUNDED,
            padding=(1, 2),
            title=f"[bold cyan]{Glyphs.SPARK} Agent REPL Ready[/bold cyan]",
            subtitle="[dim]Type a task prompt or /help to explore capabilities[/dim]",
        )
        console.print(panel)
        console.print()


class ToolCallComponent:
    """Renders a structured tool execution card with lifecycle status."""

    @staticmethod
    def render_started(console: Optional[Console], tool_name: str, args_summary: str = "") -> None:
        if not HAS_RICH or not console:
            print(f"◌ {tool_name} {args_summary}...")
            return
        t = Text()
        t.append(f"{Glyphs.PULSE} ", style="bold cyan")
        t.append(f"{tool_name} ", style="bold white")
        if args_summary:
            t.append(f"({args_summary})", style="dim")
        console.print(t)

    @staticmethod
    def render_completed(
        console: Optional[Console],
        tool_name: str,
        duration_ms: float = 0.0,
        evidence: str = "",
        verified: bool = True,
    ) -> None:
        if not HAS_RICH or not console:
            icon = "✓" if verified else "⚠"
            print(f"{icon} {tool_name} ({duration_ms:.0f}ms) — {evidence}")
            return

        icon = Glyphs.CHECK if verified else Glyphs.WARNING
        style = "bold green" if verified else "bold yellow"

        t = Text()
        t.append(f"{icon} ", style=style)
        t.append(f"{tool_name} ", style="bold white")
        t.append(f"({duration_ms:.0f}ms)", style="dim")
        if evidence:
            t.append(f" {Glyphs.CORNER} {evidence}", style="dim green" if verified else "dim yellow")
        console.print(t)

    @staticmethod
    def render_failed(
        console: Optional[Console],
        tool_name: str,
        error_msg: str,
        duration_ms: float = 0.0,
    ) -> None:
        if not HAS_RICH or not console:
            print(f"✗ {tool_name} ({duration_ms:.0f}ms) failed: {error_msg}")
            return

        t = Text()
        t.append(f"{Glyphs.CROSS} ", style="bold red")
        t.append(f"{tool_name} ", style="bold white")
        t.append(f"({duration_ms:.0f}ms) ", style="dim")
        t.append(f"failed: {error_msg}", style="red")
        console.print(t)


class CollapsibleOutputComponent:
    """Collapses long text outputs (logs, diffs, search results) to keep terminal calm."""

    @staticmethod
    def render(
        console: Optional[Console],
        title: str,
        content: str,
        max_lines: int = 8,
        syntax_lexer: Optional[str] = None,
    ) -> None:
        lines = content.strip().splitlines()
        if not HAS_RICH or not console:
            if len(lines) <= max_lines:
                print(f"[{title}]\n{content}\n")
            else:
                head = "\n".join(lines[:max_lines])
                print(f"[{title} ({len(lines)} lines total)]\n{head}\n... ({len(lines) - max_lines} lines hidden)\n")
            return

        if len(lines) <= max_lines:
            if syntax_lexer:
                console.print(Panel(Syntax(content, syntax_lexer, theme="monokai", line_numbers=True), title=title, box=ROUNDED, border_style="dim cyan"))
            else:
                console.print(Panel(content, title=title, box=ROUNDED, border_style="dim cyan"))
        else:
            preview_lines = lines[:max_lines]
            preview = "\n".join(preview_lines)
            hidden_count = len(lines) - max_lines

            text = Text()
            text.append(preview + "\n", style="white")
            text.append(f"─── {hidden_count} lines hidden (click to expand) ───", style="dim cyan italic")

            console.print(Panel(text, title=f"{title} ({len(lines)} lines)", box=ROUNDED, border_style="dim cyan"))


class PermissionPromptComponent:
    """Renders high-visibility interactive permission prompts with risk-tier warnings."""

    @staticmethod
    def render(console: Optional[Console], request: Any) -> None:
        tool = getattr(request, "tool", "unknown_tool")
        risk = getattr(request, "risk_level", "MEDIUM")
        risk_str = risk.value if hasattr(risk, "value") else str(risk)
        target = getattr(request, "target", "")
        consequence = getattr(request, "consequence", "")
        args_sum = getattr(request, "arguments_summary", "")

        if not HAS_RICH or not console:
            print("\n" + "=" * 60)
            print(f"🛡️  PERMISSION REQUIRED: {tool} [{risk_str}]")
            if target:
                print(f"Target: {target}")
            if args_sum:
                print(f"Parameters: {args_sum}")
            if consequence:
                print(f"Consequence: {consequence}")
            print("Options: [y] Allow once | [a] Allow all edits | [s] Allow for session | [d] Deny | [c] Cancel")
            print("=" * 60)
            return

        risk_color = "red" if risk_str in ("HIGH", "CRITICAL") else ("yellow" if risk_str == "MEDIUM" else "cyan")

        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)

        t_title = Text()
        t_title.append(f"{Glyphs.SHIELD}  Permission Required — ", style=f"bold {risk_color}")
        t_title.append(f"{tool} ", style="bold white")
        t_title.append(f"[{risk_str} RISK]", style=f"bold {risk_color}")
        grid.add_row(t_title)
        grid.add_row(Text(""))

        if target:
            t_target = Text()
            t_target.append("Target: ", style="bold dim")
            t_target.append(target, style="bold cyan")
            grid.add_row(t_target)

        if args_sum:
            t_args = Text()
            t_args.append("Parameters: ", style="bold dim")
            t_args.append(args_sum, style="white")
            grid.add_row(t_args)

        if consequence:
            t_con = Text()
            t_con.append("Consequence: ", style=f"bold {risk_color}")
            t_con.append(consequence, style="white")
            grid.add_row(t_con)

        grid.add_row(Text(""))
        t_opts = Text()
        t_opts.append("Actions: ", style="dim")
        t_opts.append("[y] Allow once ", style="bold green")
        t_opts.append("│ [a] Allow all edits ", style="bold green")
        t_opts.append("│ [s] Allow session ", style="bold teal")
        t_opts.append("│ [d] Deny ", style="bold red")
        t_opts.append("│ [c] Cancel", style="bold red")
        grid.add_row(t_opts)

        panel = Panel(grid, box=ROUNDED, border_style=risk_color, padding=(0, 2))
        console.print()
        console.print(panel)
        console.print()


class AlertBoxComponent:
    """Renders formatted callout boxes (Note, Tip, Warning, Caution, Important)."""

    @staticmethod
    def render(console: Optional[Console], alert_type: str, title: str, message: str) -> None:
        if not HAS_RICH or not console:
            print(f"[{alert_type.upper()}] {title}: {message}")
            return

        alert_type_lower = alert_type.lower()
        if alert_type_lower in ("warning", "warn"):
            color = COLOR_AMBER
            glyph = Glyphs.WARNING
        elif alert_type_lower in ("danger", "caution", "error"):
            color = COLOR_RED
            glyph = Glyphs.CROSS
        elif alert_type_lower in ("tip", "success"):
            color = COLOR_GREEN
            glyph = Glyphs.SPARK
        elif alert_type_lower in ("important", "accent"):
            color = COLOR_MAGENTA
            glyph = Glyphs.LIGHTNING
        else:
            color = COLOR_CYAN
            glyph = Glyphs.INFO

        t = Text()
        t.append(f"{glyph} {title}\n", style=f"bold {color}")
        t.append(message, style="white")

        panel = Panel(t, border_style=color, box=ROUNDED, padding=(0, 2))
        console.print(panel)


class PlanViewComponent:
    """Renders structured multi-step plan cards with live execution states."""

    @staticmethod
    def render(console: Optional[Console], plan: Dict[str, Any]) -> None:
        goal = plan.get("goal", "Execute Goal")
        steps = plan.get("steps", [])

        if not HAS_RICH or not console:
            print(f"\nPlan: {goal}")
            for s in steps:
                st = s.get("status", "pending")
                icon = "✓" if st == "completed" else ("◌" if st == "running" else "·")
                print(f"  {s.get('step', 1)}. {s.get('description', '')} [{icon}]")
            print()
            return

        table = Table(box=ROUNDED, border_style="cyan", show_header=True, header_style="bold cyan", expand=True)
        table.add_column("#", width=3, justify="right")
        table.add_column("Step Description", ratio=4)
        table.add_column("Tool", ratio=2)
        table.add_column("State", width=12, justify="center")

        for s in steps:
            st = s.get("status", "pending")
            if st == "completed":
                state_txt = Text(f"{Glyphs.CHECK} Done", style="bold green")
            elif st == "running":
                state_txt = Text(f"{Glyphs.PULSE} Running", style="bold cyan")
            elif st == "failed":
                state_txt = Text(f"{Glyphs.CROSS} Failed", style="bold red")
            else:
                state_txt = Text("· Pending", style="dim")

            table.add_row(
                str(s.get("step", 1)),
                s.get("description", ""),
                s.get("tool", ""),
                state_txt,
            )

        console.print(Panel(table, title=f"[bold cyan]Plan: {goal}[/bold cyan]", box=ROUNDED, border_style="cyan"))


class StatusPanelComponent:
    """Renders a high-density, calm system status report."""

    @staticmethod
    def render(console: Optional[Console], telemetry: Dict[str, Any]) -> None:
        if not HAS_RICH or not console:
            print("\n--- SYSTEM STATUS ---")
            for k, v in telemetry.items():
                print(f"{k}: {v}")
            print("--------------------\n")
            return

        grid = Table.grid(expand=True, padding=(0, 2))
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)

        left = Text()
        left.append("System Diagnostics\n", style="bold cyan")
        left.append(f"Model Gateway: {telemetry.get('gateway', 'ONLINE')}\n", style="green")
        left.append(f"EventBus: {telemetry.get('event_bus', 'HEALTHY')}\n", style="green")
        left.append(f"Memory Subsystem: {telemetry.get('memory', 'ACTIVE')}\n", style="green")

        right = Text()
        right.append("Active Session Metrics\n", style="bold cyan")
        right.append(f"Active Model: {telemetry.get('model', 'Gemini')}\n", style="white")
        right.append(f"Permission Policy: {telemetry.get('permission_mode', 'CONFIRM_DESTRUCTIVE')}\n", style="white")
        right.append(f"Tools Catalog: {telemetry.get('tools_count', 0)} registered\n", style="white")

        grid.add_row(left, right)
        console.print(Panel(grid, title="[bold cyan]BR JARVIS Subsystem Health[/bold cyan]", box=ROUNDED, border_style="cyan"))
