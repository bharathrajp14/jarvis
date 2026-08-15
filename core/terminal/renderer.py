# core/terminal/renderer.py — Visual Component Rendering Engine for BR JARVIS CLI
from __future__ import annotations

import difflib
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union

from core.terminal.theme import (
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_CYAN,
    COLOR_DARK,
    COLOR_DIM,
    COLOR_GREEN,
    COLOR_MAGENTA,
    COLOR_PANEL_BG,
    COLOR_RED,
    COLOR_TEAL,
    COLOR_WHITE,
    Glyphs,
    MODE_COLORS,
    get_terminal_theme,
)
from core.version import BUILD, CODENAME, VERSION

try:
    from rich.console import Console, Group
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text
    from rich.box import ROUNDED, HEAVY, SIMPLE, DOUBLE
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class TerminalRenderer:
    """Master Visual Renderer for BR JARVIS terminal agent interface."""

    def __init__(self, console: Optional[Console] = None):
        if HAS_RICH:
            self.console = console or Console(theme=get_terminal_theme())
        else:
            self.console = None

    def clear(self) -> None:
        """Clear console screen cleanly."""
        if HAS_RICH and self.console:
            self.console.clear()
        else:
            print("\033[H\033[J", end="")

    def print_rule(self, title: str = "", style: str = "cyan") -> None:
        if HAS_RICH and self.console:
            self.console.print(Rule(title, style=style))
        else:
            print(f"--- {title} ---" if title else "--------------------------------------------------")

    # ── Header & Banner ───────────────────────────────────────────────────────

    def render_header(self, session_info: Optional[Dict[str, Any]] = None) -> None:
        """Render top status header with metadata pills."""
        info = session_info or {}
        mode = info.get("mode", "general").lower()
        mode_color = MODE_COLORS.get(mode, COLOR_CYAN)
        model = info.get("model", "Gemini 2.5 Flash")
        session_id = info.get("session_id", "sess-default")[:8]
        perm_mode = info.get("permission_mode", "FAIL-CLOSED")
        mem_status = info.get("memory_status", "ACTIVE")

        if HAS_RICH and self.console:
            grid = Table.grid(expand=True)
            grid.add_column(justify="left", ratio=1)
            grid.add_column(justify="right", ratio=1)

            left_text = Text()
            left_text.append(f"{Glyphs.LIGHTNING} BR JARVIS ", style="bold cyan")
            left_text.append(f"v{VERSION} ", style="bold white")
            left_text.append(f"[{CODENAME}] ", style="dim")
            left_text.append(f"│ Mode: ", style="dim")
            left_text.append(f"[{mode.upper()}] ", style=f"bold {mode_color}")
            left_text.append(f"│ Model: ", style="dim")
            left_text.append(f"{model} ", style="cyan")

            right_text = Text()
            right_text.append(f"ID: ", style="dim")
            right_text.append(f"{session_id} ", style="white")
            right_text.append(f"│ Memory: ", style="dim")
            right_text.append(f"🧠 {mem_status} ", style="green")
            right_text.append(f"│ Security: ", style="dim")
            right_text.append(f"{Glyphs.SHIELD} {perm_mode}", style="bold green")

            grid.add_row(left_text, right_text)

            panel = Panel(
                grid,
                border_style=COLOR_CYAN,
                box=ROUNDED,
                padding=(0, 1),
            )
            self.console.print(panel)
        else:
            print(f"[{Glyphs.LIGHTNING} BR JARVIS v{VERSION} | Mode: {mode.upper()} | Model: {model} | ID: {session_id} | Security: {perm_mode}]")

    def render_welcome(self) -> None:
        """Render welcoming agent dashboard with shortcuts."""
        if HAS_RICH and self.console:
            text = Text()
            text.append("⚡ BR JARVIS MK40.2 Autonomous Cognitive Agent Terminal\n", style="bold cyan")
            text.append("Connected to UnifiedMemory, Dynamic Tool Registry, and Sandbox ActionVerifier.\n\n", style="dim")
            text.append("Quick Commands:\n", style="bold white")
            text.append("  /help            ", style="bold cyan")
            text.append("Show full command reference and keyboard shortcuts\n", style="dim")
            text.append("  /mode <name>     ", style="bold cyan")
            text.append("Switch persona: coder, analyst, recon, planner, exploit, general\n", style="dim")
            text.append("  /tasks           ", style="bold cyan")
            text.append("Inspect background and multi-stage task lifecycle records\n", style="dim")
            text.append("  /memory <subcmd> ", style="bold cyan")
            text.append("Query unified memory: search <q>, recent, project, stats\n", style="dim")
            text.append("  /doctor          ", style="bold cyan")
            text.append("Run self-healing diagnostics and verify system integrity\n", style="dim")
            text.append("  /quit            ", style="bold cyan")
            text.append("Consolidate session learnings and exit cleanly\n", style="dim")

            panel = Panel(
                text,
                border_style=COLOR_BLUE,
                box=ROUNDED,
                padding=(0, 2),
                title="[bold yellow]Agent REPL Initialized[/bold yellow]",
            )
            self.console.print(panel)
            self.console.print()
        else:
            print("==================================================================")
            print(f" BR JARVIS v{VERSION} Cognitive Agent Terminal")
            print(" Commands: /help, /mode <name>, /tasks, /memory, /doctor, /quit")
            print("==================================================================")

    # ── Tool Execution Visual Card ────────────────────────────────────────────

    def render_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        status: str = "COMPLETED",
        duration_ms: float = 0.0,
        verified: bool = False,
        evidence: str = "",
    ) -> None:
        """Render a formatted tool invocation and execution card."""
        is_success = "error" not in str(status).lower() and "fail" not in str(status).lower()
        status_color = COLOR_GREEN if is_success else COLOR_RED
        status_symbol = Glyphs.CHECK if is_success else Glyphs.CROSS
        badge_text = f"[{status_color}]{status_symbol} {status}[/]"

        if HAS_RICH and self.console:
            table = Table.grid(expand=True)
            table.add_column(ratio=3)
            table.add_column(justify="right", ratio=1)

            header_left = Text()
            header_left.append(f"{Glyphs.TOOL} Tool: ", style="dim")
            header_left.append(tool_name, style="bold cyan")
            
            header_right = Text()
            if duration_ms > 0:
                header_right.append(f"{duration_ms:.0f}ms │ ", style="dim")
            header_right.append(f"{status_symbol} {status}", style=f"bold {status_color}")

            table.add_row(header_left, header_right)

            # Argument formatted preview
            body_parts = []
            if args:
                args_text = Text()
                args_text.append("Arguments:\n", style="dim cyan")
                for k, v in list(args.items())[:5]:
                    val_str = str(v).replace("\n", " ").strip()
                    if len(val_str) > 80:
                        val_str = val_str[:77] + "..."
                    args_text.append(f"  • {k}: ", style="teal")
                    args_text.append(f"{val_str}\n", style="white")
                body_parts.append(args_text)

            # Result preview
            if result is not None:
                res_str = str(result).strip()
                if len(res_str) > 500:
                    res_str = res_str[:400] + "\n... [truncated for display] ..."
                res_text = Text()
                res_text.append("Output:\n", style="dim green" if is_success else "dim red")
                res_text.append(f"{res_str}\n", style="dim" if is_success else "bold red")
                body_parts.append(res_text)

            # Verification badge if applicable
            if verified or evidence:
                v_text = Text()
                v_text.append(f"{Glyphs.SHIELD} Verification: ", style="bold green")
                v_text.append(evidence or "Verified on disk / process", style="green")
                body_parts.append(v_text)

            content_group = Group(table, *body_parts)
            card = Panel(
                content_group,
                border_style=COLOR_CYAN if is_success else COLOR_RED,
                box=ROUNDED,
                padding=(0, 1),
            )
            self.console.print(card)
        else:
            print(f"[{Glyphs.TOOL} {tool_name}] {status} ({duration_ms:.0f}ms)")
            if args:
                print(f"  Args: {json.dumps(args, default=str)[:100]}")
            if result:
                print(f"  Result: {str(result)[:150]}")
            if verified:
                print(f"  {Glyphs.SHIELD} Verified: {evidence}")

    # ── Verification Result Card ──────────────────────────────────────────────

    def render_verification(self, verification_result: Any) -> None:
        """Render explicit ActionVerifier outcome."""
        verified = getattr(verification_result, "verified", False)
        status = getattr(verification_result, "status", "SUCCESS" if verified else "FAILED")
        status_val = getattr(status, "value", str(status))
        evidence = getattr(verification_result, "evidence", "") or getattr(verification_result, "details", "")
        error = getattr(verification_result, "error", None)

        color = COLOR_GREEN if verified else COLOR_RED
        symbol = Glyphs.CHECK if verified else Glyphs.CROSS

        if HAS_RICH and self.console:
            text = Text()
            text.append(f"{Glyphs.SHIELD} Action Verification: ", style="bold")
            text.append(f"[{status_val}] {symbol}\n", style=f"bold {color}")
            if evidence:
                text.append(f"Evidence: {evidence}\n", style="dim")
            if error:
                text.append(f"Error: {error}\n", style="bold red")

            panel = Panel(text, border_style=color, box=ROUNDED, padding=(0, 1))
            self.console.print(panel)
        else:
            print(f"[{Glyphs.SHIELD} VERIFICATION: {status_val}] {evidence}")

    # ── File Diff Visualizer ──────────────────────────────────────────────────

    def render_diff(self, file_path: str, old_content: str, new_content: str) -> None:
        """Render syntax-highlighted unified diff for file edits."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}"))

        if not diff:
            return

        diff_text = "".join(diff)
        if HAS_RICH and self.console:
            syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
            panel = Panel(
                syntax,
                title=f"[bold yellow]Diff: {file_path}[/bold yellow]",
                border_style=COLOR_CYAN,
                box=ROUNDED,
                padding=(0, 1),
            )
            self.console.print(panel)
        else:
            print(f"--- Diff: {file_path} ---")
            print(diff_text)

    # ── Stage Progress Timeline ───────────────────────────────────────────────

    def render_stage_progress(self, stages: List[Dict[str, Any]], current_idx: int, total_stages: int) -> None:
        """Render composite multi-stage task breakdown progress."""
        if HAS_RICH and self.console:
            table = Table(title=f"Multi-Stage Task Plan ({current_idx}/{total_stages} Active)", border_style=COLOR_CYAN, box=ROUNDED)
            table.add_column("Stage", style="bold cyan", width=8)
            table.add_column("Goal / Subtask", style="white")
            table.add_column("Assigned Agent", style="dim")
            table.add_column("Status", justify="center", width=12)

            for i, st in enumerate(stages):
                idx_str = f"#{i+1}"
                name = st.get("name") or st.get("goal") or f"Stage {i+1}"
                agent = st.get("agent_type", "general")
                if i < current_idx - 1:
                    status_badge = f"[green]{Glyphs.CHECK} Done[/]"
                elif i == current_idx - 1:
                    status_badge = f"[bold yellow]{Glyphs.PLAY} Running[/]"
                else:
                    status_badge = f"[dim]○ Pending[/]"
                table.add_row(idx_str, name[:60], agent, status_badge)

            self.console.print(table)
        else:
            print(f"--- Task Stages ({current_idx}/{total_stages}) ---")
            for i, st in enumerate(stages):
                status_char = "[X]" if i < current_idx - 1 else "[>]" if i == current_idx - 1 else "[ ]"
                print(f"  {status_char} #{i+1}: {st.get('goal', '')[:50]}")

    # ── Memory & Lessons Card ─────────────────────────────────────────────────

    def render_memory_card(self, memories: List[Dict[str, Any]], title: str = "Recalled Context & Lessons") -> None:
        """Render retrieved memory entries card."""
        if not memories:
            return
        if HAS_RICH and self.console:
            text = Text()
            text.append(f"{Glyphs.BRAIN} {title}\n", style="bold magenta")
            for m in memories:
                m_type = m.get("type", m.get("source", "memory")).upper()
                name = m.get("name", "")
                content = m.get("content", "")[:140].replace("\n", " ")
                text.append(f"  • [{m_type}] ", style="bold cyan")
                if name:
                    text.append(f"{name}: ", style="white")
                text.append(f"{content}\n", style="dim")

            panel = Panel(text, border_style=COLOR_MAGENTA, box=ROUNDED, padding=(0, 1))
            self.console.print(panel)
        else:
            print(f"[{Glyphs.BRAIN} {title}]")
            for m in memories:
                print(f"  • [{m.get('type','').upper()}] {m.get('content','')[:80]}")

    # ── Tables (Status, Tasks, Tools) ─────────────────────────────────────────

    def render_status_table(self, data: Dict[str, Any]) -> None:
        """Render comprehensive subsystem status report."""
        if HAS_RICH and self.console:
            table = Table(title="Subsystem Diagnostics & Health", border_style=COLOR_CYAN, box=ROUNDED)
            table.add_column("Subsystem", style="bold cyan", width=22)
            table.add_column("Status / Details", style="white")

            for k, v in data.items():
                if isinstance(v, bool):
                    v_str = "[green]✓ ONLINE[/]" if v else "[red]✗ OFFLINE[/]"
                else:
                    v_str = str(v)
                table.add_row(k, v_str)

            self.console.print(table)
        else:
            print("--- Subsystem Status ---")
            for k, v in data.items():
                print(f"  {k}: {v}")

    def render_tasks_table(self, tasks: List[Any]) -> None:
        """Render recent tasks table."""
        if HAS_RICH and self.console:
            table = Table(title="Task Lifecycle Records", border_style=COLOR_CYAN, box=ROUNDED)
            table.add_column("Task ID", style="dim", width=12)
            table.add_column("Goal / Instruction", style="bold white")
            table.add_column("Status", justify="center", width=14)
            table.add_column("Progress", justify="center", width=10)

            for t in tasks:
                t_id = getattr(t, "task_id", str(t.get("task_id", "")))[:10]
                goal = getattr(t, "goal", str(t.get("goal", "")))[:60]
                status = getattr(t, "status", t.get("status", "unknown"))
                status_str = getattr(status, "value", str(status))
                curr_step = getattr(t, "current_step", t.get("current_step", 0))
                total_steps = getattr(t, "total_steps", t.get("total_steps", 1))

                status_style = "green" if "complete" in status_str.lower() else "yellow" if "run" in status_str.lower() else "red"
                table.add_row(t_id, goal, f"[{status_style}]{status_str.upper()}[/]", f"{curr_step}/{total_steps}")

            self.console.print(table)
        else:
            print("--- Task Lifecycle Records ---")
            for t in tasks:
                t_id = getattr(t, "task_id", str(t.get("task_id", "")))[:10]
                goal = getattr(t, "goal", str(t.get("goal", "")))[:40]
                print(f"  [{t_id}] {goal}")

    def render_tools_table(self, tools: List[Dict[str, Any]], filter_query: str = "") -> None:
        """Render registered tools catalog."""
        filtered = tools
        if filter_query:
            q = filter_query.lower()
            filtered = [t for t in tools if q in t.get("name", "").lower() or q in t.get("description", "").lower()]

        if HAS_RICH and self.console:
            title = f"Tool Registry Catalog ({len(filtered)} tools)"
            if filter_query:
                title += f" [Filter: '{filter_query}']"
            table = Table(title=title, border_style=COLOR_CYAN, box=ROUNDED)
            table.add_column("Tool Name", style="bold cyan", width=22)
            table.add_column("Description", style="white")
            table.add_column("Category", style="dim", width=14)
            table.add_column("Risk", justify="center", width=8)

            for t in filtered[:35]:
                name = t.get("name", "")
                desc = t.get("description", "")[:70]
                cat = t.get("category", "General")
                risk = t.get("risk_level", "LOW")
                risk_style = "green" if risk == "LOW" else "yellow" if risk == "MEDIUM" else "red"
                table.add_row(name, desc, cat, f"[{risk_style}]{risk}[/]")

            self.console.print(table)
            if len(filtered) > 35:
                self.console.print(f"[dim]... and {len(filtered) - 35} more tools. Use /tools <search> to refine.[/dim]")
        else:
            print(f"--- Registered Tools ({len(filtered)}) ---")
            for t in filtered[:20]:
                print(f"  {t.get('name')}: {t.get('description')[:50]}")

    # ── Markdown & Natural Language ───────────────────────────────────────────

    def render_markdown(self, markdown_text: str) -> None:
        """Render rich markdown with formatted code blocks."""
        if not markdown_text:
            return
        if HAS_RICH and self.console:
            md = Markdown(markdown_text)
            self.console.print(md)
        else:
            print(markdown_text)

    def render_error(self, title: str, message: str, suggestions: Optional[List[str]] = None) -> None:
        """Render error box with guidance."""
        if HAS_RICH and self.console:
            text = Text()
            text.append(f"{Glyphs.CROSS} {title}\n", style="bold red")
            text.append(f"{message}\n\n", style="white")
            if suggestions:
                text.append("Suggested Remediation:\n", style="bold yellow")
                for s in suggestions:
                    text.append(f"  • {s}\n", style="dim yellow")

            panel = Panel(text, border_style=COLOR_RED, box=ROUNDED, padding=(0, 1))
            self.console.print(panel)
        else:
            print(f"[ERROR] {title}: {message}")
            if suggestions:
                for s in suggestions:
                    print(f"  - {s}")
