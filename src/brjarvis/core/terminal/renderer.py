# core/terminal/renderer.py — Visual Component Rendering Engine for BR JARVIS CLI
from __future__ import annotations

import difflib
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union

from .theme import (
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
from ..version import BUILD, CODENAME, VERSION

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

    # ══════════════════════════════════════════════════════════════════════════
    # MK41 NEW RENDERER PANELS
    # ══════════════════════════════════════════════════════════════════════════

    # ── Enhanced Welcome ──────────────────────────────────────────────────────

    def render_welcome(self) -> None:
        """Render MK41 welcoming agent dashboard with shortcuts."""
        if HAS_RICH and self.console:
            text = Text()
            text.append("⚡ BR JARVIS MK41 — Autonomous Cognitive Agent Terminal\n", style="bold cyan")
            text.append("Connected to UnifiedMemory, Tool Registry, and Sandbox ActionVerifier.\n\n", style="dim")
            text.append("Quick Reference:\n", style="bold white")
            cmds = [
                ("/plan <goal>",   "Decompose goal into plan → approve → execute"),
                ("/mode <name>",   "Switch persona: coder, analyst, researcher, planner, automation"),
                ("/tasks",         "Live task dashboard with step progress"),
                ("/memory <sub>",  "search <q> | recent | project | stats | forget <id>"),
                ("/doctor",        "Interactive system health check"),
                ("/permission",    "View or set permission mode"),
                ("/help",          "Full command reference"),
                ("/quit",          "Consolidate learnings and exit"),
            ]
            for cmd, desc in cmds:
                text.append(f"  {cmd:<22}", style="bold cyan")
                text.append(f"{desc}\n", style="dim")
            text.append("\nType a goal directly to begin, or use /plan for explicit approval mode.", style="dim italic")

            panel = Panel(
                text,
                border_style=COLOR_BLUE,
                box=ROUNDED,
                padding=(0, 2),
                title="[bold yellow]⚡ Agent REPL Initialized[/bold yellow]",
            )
            self.console.print(panel)
            self.console.print()
        else:
            print("=" * 66)
            print(f" ⚡ BR JARVIS MK41 | Commands: /plan /mode /tasks /memory /help /quit")
            print("=" * 66)

    # ── Plan Panel (Phase 3) ──────────────────────────────────────────────────

    def render_plan_panel(
        self,
        goal: str,
        steps: List[str],
        risk: str = "Medium",
        external_actions: Optional[List[str]] = None,
        plan_id: Optional[str] = None,
    ) -> None:
        """Render an interactive plan card before approval."""
        if HAS_RICH and self.console:
            text = Text()
            text.append(f"Goal: ", style="bold white")
            text.append(f"{goal}\n\n", style="cyan")
            for i, step in enumerate(steps, 1):
                text.append(f"  {i:2d}. ", style="dim")
                text.append(f"{step}\n", style="white")
            text.append(f"\n  Risk: ", style="dim")
            risk_style = "green" if risk.lower() == "low" else "yellow" if risk.lower() == "medium" else "red"
            text.append(f"{risk}", style=f"bold {risk_style}")
            if external_actions:
                text.append(f"  │  External: ", style="dim")
                text.append(", ".join(external_actions), style="yellow")
            if plan_id:
                text.append(f"\n  Plan ID: ", style="dim")
                text.append(plan_id, style="dim cyan")
            text.append("\n\n")
            text.append("  [Enter] Approve  ", style="bold green")
            text.append("[e] Edit  ", style="bold yellow")
            text.append("[r] Re-plan  ", style="bold cyan")
            text.append("[c] Cancel", style="bold red")

            panel = Panel(
                text,
                border_style=COLOR_CYAN,
                box=ROUNDED,
                padding=(0, 1),
                title="[bold cyan]◆ PLAN READY[/bold cyan]",
            )
            self.console.print(panel)
        else:
            print(f"\n--- PLAN: {goal} ---")
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step}")
            print(f"  Risk: {risk}")
            print("  [Enter] Approve  [e] Edit  [r] Re-plan  [c] Cancel")

    def prompt_plan_approval(self) -> str:
        """Prompt user for plan approval. Returns: 'approve'|'edit'|'replan'|'cancel'."""
        if HAS_RICH and self.console:
            from rich.prompt import Prompt as RPrompt
            try:
                choice = RPrompt.ask(
                    "\n  [bold green]Approve plan?[/bold green]",
                    choices=["", "y", "e", "r", "c", "q", "quit", "exit"],
                    default="y",
                    show_choices=False,
                ).strip().lower()
            except (KeyboardInterrupt, EOFError):
                return "cancel"
        else:
            try:
                choice = input("\n  Approve plan? [Y/e/r/c/q]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                return "cancel"

        if choice in ("", "y", "yes"):
            return "approve"
        if choice in ("e", "edit"):
            return "edit"
        if choice in ("r", "replan"):
            return "replan"
        return "cancel"

    # ── Permission Prompt Panel (Phase 4) ────────────────────────────────────

    def render_permission_prompt(
        self,
        tool_name: str,
        target: str,
        action: str,
        risk: str = "External side effect",
        task_context: str = "",
    ) -> str:
        """Render interactive permission request panel. Returns: 'allow'|'always'|'deny'|'show_plan'."""
        if HAS_RICH and self.console:
            text = Text()
            text.append(f"  Tool:   ", style="dim")
            text.append(f"{tool_name}\n", style="bold cyan")
            text.append(f"  Target: ", style="dim")
            text.append(f"{target}\n", style="white")
            text.append(f"  Action: ", style="dim")
            text.append(f"{action}\n", style="white")
            text.append(f"  Risk:   ", style="dim")
            text.append(f"{risk}\n", style="bold yellow")
            if task_context:
                text.append(f"  Task:   ", style="dim")
                text.append(f"{task_context[:60]}\n", style="dim")
            text.append("\n")
            text.append("  [Y] Allow once   ", style="bold green")
            text.append("[A] Always allow   ", style="bold cyan")
            text.append("[N] Deny   ", style="bold red")
            text.append("[S] Show plan", style="bold yellow")

            panel = Panel(
                text,
                border_style=COLOR_AMBER,
                box=ROUNDED,
                padding=(0, 1),
                title="[bold yellow]🛡️  Permission Required[/bold yellow]",
            )
            self.console.print(panel)
            from rich.prompt import Prompt as RPrompt
            try:
                choice = RPrompt.ask(
                    "  Decision",
                    choices=["y", "Y", "a", "A", "n", "N", "s", "S", "q", "Q", "quit", "exit"],
                    default="y",
                    show_choices=False,
                ).strip().upper()
            except (KeyboardInterrupt, EOFError):
                return "deny"
        else:
            print(f"\n[PERMISSION] Tool: {tool_name} | Target: {target} | Risk: {risk}")
            print("  [Y] Allow once  [A] Always  [N] Deny  [S] Show plan")
            try:
                choice = input("  Decision [Y/a/n/s/q]: ").strip().upper() or "Y"
            except (KeyboardInterrupt, EOFError):
                return "deny"

        if choice in ("Y", ""):
            return "allow"
        if choice == "A":
            return "always"
        if choice == "S":
            return "show_plan"
        return "deny"

    # ── Recovery UI Panel (Phase 12) ──────────────────────────────────────────

    def render_recovery_ui(
        self,
        failed_tool: str,
        reason: str,
        completed_steps: List[str],
        failed_step: str,
        task_id: str = "",
    ) -> str:
        """Render task failure recovery panel. Returns: 'retry'|'authenticate'|'continue'|'cancel'."""
        if HAS_RICH and self.console:
            text = Text()
            text.append(f"  {failed_tool} failed\n", style="bold red")
            text.append(f"  Reason: {reason}\n\n", style="white")
            for step in completed_steps:
                text.append(f"  {Glyphs.CHECK} {step}\n", style="green")
            text.append(f"  {Glyphs.CROSS} {failed_step}\n\n", style="bold red")
            if task_id:
                text.append(f"  Task: {task_id}\n\n", style="dim")
            text.append("  [R] Retry   ", style="bold cyan")
            text.append("[A] Authenticate   ", style="bold yellow")
            text.append("[C] Continue without   ", style="bold green")
            text.append("[X] Cancel", style="bold red")

            panel = Panel(
                text,
                border_style=COLOR_RED,
                box=ROUNDED,
                padding=(0, 1),
                title="[bold red]⚠ RECOVERY REQUIRED[/bold red]",
            )
            self.console.print(panel)
            from rich.prompt import Prompt as RPrompt
            try:
                choice = RPrompt.ask(
                    "  Action",
                    choices=["r", "R", "a", "A", "c", "C", "x", "X", "q", "Q", "quit", "exit"],
                    default="r",
                    show_choices=False,
                ).strip().upper()
            except (KeyboardInterrupt, EOFError):
                return "cancel"
        else:
            print(f"\n[RECOVERY] {failed_tool} failed: {reason}")
            for s in completed_steps:
                print(f"  ✓ {s}")
            print(f"  ✗ {failed_step}")
            print("  [R] Retry  [A] Authenticate  [C] Continue  [X] Cancel")
            try:
                choice = input("  Action [R/a/c/x/q]: ").strip().upper() or "R"
            except (KeyboardInterrupt, EOFError):
                return "cancel"

        if choice == "R":
            return "retry"
        if choice == "A":
            return "authenticate"
        if choice == "C":
            return "continue"
        return "cancel"

    # ── Plan vs Actual comparison (Phase 13) ─────────────────────────────────

    def render_plan_vs_actual(
        self,
        planned_steps: List[str],
        completed_steps: List[str],
        failed_steps: List[str],
        skipped_steps: List[str],
        final_status: str,
        task_id: str = "",
    ) -> None:
        """Render side-by-side plan vs actual execution comparison."""
        if HAS_RICH and self.console:
            table = Table(
                title=f"Task Completion Report{' — ' + task_id if task_id else ''}",
                border_style=COLOR_CYAN,
                box=ROUNDED,
                show_header=True,
            )
            table.add_column("#", style="dim", width=4, justify="right")
            table.add_column("Planned Step", style="white")
            table.add_column("Result", justify="center", width=16)

            for i, step in enumerate(planned_steps, 1):
                step_lower = step.lower()
                if any(step_lower in s.lower() or s.lower() in step_lower for s in completed_steps):
                    result = f"[green]{Glyphs.CHECK} Done[/green]"
                elif any(step_lower in s.lower() or s.lower() in step_lower for s in failed_steps):
                    result = f"[red]{Glyphs.CROSS} Failed[/red]"
                elif any(step_lower in s.lower() or s.lower() in step_lower for s in skipped_steps):
                    result = f"[dim]○ Skipped[/dim]"
                else:
                    result = f"[dim]○ Not executed[/dim]"
                table.add_row(str(i), step[:55], result)

            self.console.print(table)

            status_style = (
                "bold green" if "success" in final_status.lower()
                else "bold yellow" if "partial" in final_status.lower()
                else "bold red"
            )
            self.console.print(f"\n[{status_style}]Final Status: {final_status}[/{status_style}]\n")
        else:
            print("\n--- PLAN vs ACTUAL ---")
            for i, step in enumerate(planned_steps, 1):
                if step in completed_steps:
                    marker = "✓"
                elif step in failed_steps:
                    marker = "✗"
                else:
                    marker = "○"
                print(f"  {marker} {i}. {step}")
            print(f"\nFinal Status: {final_status}")

    # ── Task Detail Panel (Phase 5) ───────────────────────────────────────────

    def render_task_detail(self, task: Any) -> None:
        """Render comprehensive task detail card."""
        if not task:
            self.render_error("Task Not Found", "No task record found with that ID.")
            return

        task_id = getattr(task, "task_id", "?")
        goal = getattr(task, "goal", getattr(task, "user_request", ""))
        status = getattr(task, "status", "unknown")
        status_str = getattr(status, "value", str(status))
        created = getattr(task, "created_at", 0)
        updated = getattr(task, "updated_at", 0)
        actions = getattr(task, "actions", [])
        planned = getattr(task, "planned_steps", [])
        completed = getattr(task, "completed_steps", [])
        failed = getattr(task, "failed_steps", [])
        artifacts = getattr(task, "artifacts", [])
        error_info = getattr(task, "error_info", None)

        if HAS_RICH and self.console:
            import datetime
            text = Text()
            text.append(f"Task ID: ", style="dim")
            text.append(f"{task_id}\n", style="bold cyan")
            text.append(f"Goal:    ", style="dim")
            text.append(f"{goal[:80]}\n\n", style="bold white")

            status_style = (
                "bold green" if "success" in status_str.lower()
                else "bold yellow" if any(x in status_str.lower() for x in ["run", "plan", "wait"])
                else "bold red"
            )
            text.append(f"Status:  ", style="dim")
            text.append(f"{status_str}\n", style=status_style)

            if created:
                created_str = datetime.datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")
                text.append(f"Created: ", style="dim")
                text.append(f"{created_str}\n", style="dim")

            # Steps
            if planned or actions:
                text.append(f"\nSteps:\n", style="bold white")
                for i, act in enumerate(actions[:20], 1):
                    act_status = getattr(act, "status", act.get("status", "?") if isinstance(act, dict) else "?")
                    act_tool = getattr(act, "tool", act.get("tool", "?") if isinstance(act, dict) else "?")
                    if act_status in ("completed", "done", "success"):
                        sym, col = Glyphs.CHECK, "green"
                    elif act_status in ("failed", "error"):
                        sym, col = Glyphs.CROSS, "red"
                    else:
                        sym, col = "→", "yellow"
                    text.append(f"  [{col}]{sym} {act_tool}[/{col}]\n")

            # Artifacts
            if artifacts:
                text.append(f"\nArtifacts ({len(artifacts)}):\n", style="bold white")
                for art in artifacts[:8]:
                    path = art.get("path", art.get("host_path", "?")) if isinstance(art, dict) else str(art)
                    text.append(f"  {Glyphs.CHECK} {path}\n", style="green")

            # Error
            if error_info:
                reason = error_info.get("reason", str(error_info))[:120] if isinstance(error_info, dict) else str(error_info)[:120]
                text.append(f"\nError: {reason}\n", style="bold red")
                text.append("Use /retry <task_id> to attempt recovery.\n", style="dim yellow")

            panel = Panel(
                text,
                border_style=COLOR_CYAN,
                box=ROUNDED,
                padding=(0, 1),
                title=f"[bold cyan]Task Detail: {task_id[:12]}[/bold cyan]",
            )
            self.console.print(panel)
        else:
            print(f"\n[Task {task_id}] {goal}\nStatus: {status_str}")
            for act in actions[:10]:
                print(f"  - {getattr(act, 'tool', '?')}")

    # ── Artifact Panel (Phase 5) ──────────────────────────────────────────────

    def render_artifact_panel(self, artifacts: List[Dict[str, Any]], verified: bool = True) -> None:
        """Render artifact creation summary panel."""
        if not artifacts:
            return

        if HAS_RICH and self.console:
            text = Text()
            for art in artifacts:
                path = art.get("path", art.get("host_path", str(art)))
                name = art.get("name", path.split("/")[-1] if "/" in path else path.split("\\")[-1])
                v = art.get("verified", verified)
                sym = f"[green]{Glyphs.CHECK}[/green]" if v else f"[yellow]○[/yellow]"
                text.append(f"  {sym} {name}\n")
            text.append(f"\n  [O] Open   [V] Verify   [D] Diff   [S] Show path", style="dim")

            panel = Panel(
                text,
                border_style=COLOR_GREEN,
                box=ROUNDED,
                padding=(0, 1),
                title=f"[bold green]{Glyphs.CHECK} ARTIFACTS ({len(artifacts)})[/bold green]",
            )
            self.console.print(panel)
        else:
            print(f"\nArtifacts ({len(artifacts)}):")
            for art in artifacts:
                print(f"  ✓ {art.get('path', str(art))}")

    # ── Human-in-the-Loop Question Panel ────────────────────────────────────

    def render_question_panel(
        self,
        question: str,
        choices: Optional[List[str]] = None,
    ) -> str:
        """Render an agent-initiated question panel and return user answer."""
        if HAS_RICH and self.console:
            text = Text()
            text.append(f"  {question}\n", style="white")
            if choices:
                text.append("\n", style="")
                for i, choice in enumerate(choices, 1):
                    text.append(f"  {i}. {choice}\n", style="cyan")

            panel = Panel(
                text,
                border_style=COLOR_MAGENTA,
                box=ROUNDED,
                padding=(0, 1),
                title="[bold magenta]INPUT REQUIRED[/bold magenta]",
            )
            self.console.print(panel)
            from rich.prompt import Prompt as RPrompt
            try:
                answer = RPrompt.ask("  Your answer").strip()
            except (KeyboardInterrupt, EOFError):
                return ""
        else:
            print(f"\n[INPUT REQUIRED] {question}")
            if choices:
                for i, c in enumerate(choices, 1):
                    print(f"  {i}. {c}")
            try:
                answer = input("  Your answer: ").strip()
            except (KeyboardInterrupt, EOFError):
                return ""

        return answer

    # ── Doctor Report Panel (Phase 11) ───────────────────────────────────────

    def render_doctor_report(self, checks: List[Dict[str, Any]], overall: str) -> None:
        """Render interactive doctor diagnostic report."""
        if HAS_RICH and self.console:
            text = Text()
            text.append("BR JARVIS SYSTEM CHECK\n\n", style="bold cyan")
            for check in checks:
                name = check.get("name", "?")
                ok = check.get("ok", False)
                detail = check.get("detail", "")
                if ok:
                    text.append(f"  {Glyphs.CHECK} {name}", style="green")
                else:
                    text.append(f"  {Glyphs.CROSS} {name}", style="bold red")
                if detail:
                    text.append(f" — {detail}", style="dim")
                text.append("\n")

            text.append(f"\nOverall: ", style="bold white")
            status_style = "bold green" if overall == "HEALTHY" else "bold yellow" if "DEGRADED" in overall else "bold red"
            text.append(f"{overall}", style=status_style)

            panel = Panel(
                text,
                border_style=COLOR_CYAN,
                box=ROUNDED,
                padding=(0, 1),
                title="[bold cyan]🩺 System Diagnostics[/bold cyan]",
            )
            self.console.print(panel)
        else:
            print("\nBR JARVIS SYSTEM CHECK")
            for check in checks:
                sym = "✓" if check.get("ok") else "✗"
                print(f"  {sym} {check.get('name')} — {check.get('detail', '')}")
            print(f"\nOverall: {overall}")

    # ── Connector Status Table (Phase 10) ────────────────────────────────────

    def render_connectors_table(self, connectors: List[Dict[str, Any]]) -> None:
        """Render connector authentication & status table."""
        if HAS_RICH and self.console:
            table = Table(
                title="Connector Registry",
                border_style=COLOR_CYAN,
                box=ROUNDED,
            )
            table.add_column("Connector", style="bold cyan", width=18)
            table.add_column("Status", justify="center", width=16)
            table.add_column("Capabilities", style="dim")

            for conn in connectors:
                name = conn.get("name", "?")
                status = conn.get("status", "unknown")
                caps = ", ".join(conn.get("capabilities", []))[:50]

                if status == "connected":
                    status_cell = f"[green]{Glyphs.CHECK} Connected[/green]"
                elif status == "auth_required":
                    status_cell = f"[yellow]⚠ Auth Required[/yellow]"
                elif status == "degraded":
                    status_cell = f"[yellow]⚠ Degraded[/yellow]"
                elif status == "disabled":
                    status_cell = f"[dim]○ Disabled[/dim]"
                else:
                    status_cell = f"[red]{Glyphs.CROSS} Unavailable[/red]"
                table.add_row(name, status_cell, caps)

            self.console.print(table)
        else:
            print("--- Connectors ---")
            for conn in connectors:
                print(f"  {conn.get('name')}: {conn.get('status')}")

    # ── Model Selector Panel (Phase 9) ───────────────────────────────────────

    def render_model_table(self, models: List[Dict[str, Any]], active: str = "") -> None:
        """Render model/backend selector table."""
        if HAS_RICH and self.console:
            table = Table(
                title="AI Backend Registry",
                border_style=COLOR_CYAN,
                box=ROUNDED,
            )
            table.add_column("Backend", style="bold cyan", width=16)
            table.add_column("Model", style="white", width=24)
            table.add_column("Status", justify="center", width=14)
            table.add_column("Context", justify="right", width=10)
            table.add_column("Capabilities", style="dim")

            for m in models:
                name = m.get("name", "?")
                model = m.get("model", "?")
                status = m.get("status", "unknown")
                context = m.get("context", "?")
                caps = ", ".join(m.get("capabilities", []))[:40]
                is_active = (name.lower() == active.lower())

                if status == "available":
                    status_cell = f"[green]{Glyphs.CHECK} Online[/green]"
                elif status == "no_key":
                    status_cell = f"[yellow]⚠ No API Key[/yellow]"
                else:
                    status_cell = f"[red]{Glyphs.CROSS} Unavailable[/red]"

                name_cell = f"[bold yellow]► {name}[/bold yellow]" if is_active else name
                table.add_row(name_cell, model, status_cell, str(context), caps)

            self.console.print(table)
        else:
            print("--- AI Backends ---")
            for m in models:
                active_marker = "►" if m.get("name", "").lower() == active.lower() else " "
                print(f"  {active_marker} {m.get('name')}: {m.get('model')} [{m.get('status')}]")

    # ── Usage Stats Panel (Phase 9) ───────────────────────────────────────────

    def render_usage_stats(self, stats: Dict[str, Any]) -> None:
        """Render token/request usage stats panel."""
        if HAS_RICH and self.console:
            text = Text()
            for k, v in stats.items():
                text.append(f"  {k:<24}", style="dim")
                text.append(f"{v}\n", style="white")

            panel = Panel(
                text,
                border_style=COLOR_TEAL,
                box=ROUNDED,
                padding=(0, 1),
                title="[bold cyan]📊 Session Usage[/bold cyan]",
            )
            self.console.print(panel)
        else:
            print("\n--- Usage Stats ---")
            for k, v in stats.items():
                print(f"  {k}: {v}")

    # ── Success Verified Banner ───────────────────────────────────────────────

    def render_success_banner(
        self,
        title: str = "SUCCESS_VERIFIED",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render prominent success banner for verified task completion."""
        if HAS_RICH and self.console:
            text = Text()
            text.append(f"\n  {Glyphs.CHECK} {title}\n", style="bold green")
            if details:
                text.append("\n", style="")
                for k, v in details.items():
                    text.append(f"  {k}: ", style="dim")
                    text.append(f"{v}\n", style="white")

            panel = Panel(
                text,
                border_style=COLOR_GREEN,
                box=ROUNDED,
                padding=(0, 1),
            )
            self.console.print(panel)
        else:
            print(f"\n✓ {title}")
            if details:
                for k, v in details.items():
                    print(f"  {k}: {v}")

    # ── Step Progress Line (streaming) ───────────────────────────────────────

    def print_step_progress(self, step: str, status: str = "running", duration_ms: float = 0.0) -> None:
        """Print a single live step progress line."""
        if HAS_RICH and self.console:
            if status == "running":
                self.console.print(f"[bold cyan]→[/bold cyan] [white]{step}[/white]")
            elif status == "done":
                dur = f" ({duration_ms:.0f}ms)" if duration_ms else ""
                self.console.print(f"[green]{Glyphs.CHECK}[/green] [dim]{step}{dur}[/dim]")
            elif status == "failed":
                self.console.print(f"[red]{Glyphs.CROSS}[/red] [bold red]{step}[/bold red]")
        else:
            sym = "→" if status == "running" else "✓" if status == "done" else "✗"
            print(f"{sym} {step}")

    # ── Context Panel (Phase 7) ───────────────────────────────────────────────

    def render_context_panel(self, context: Dict[str, Any]) -> None:
        """Render current session context summary."""
        if HAS_RICH and self.console:
            text = Text()
            for k, v in context.items():
                text.append(f"  {k:<28}", style="bold cyan")
                text.append(f"{v}\n", style="white")

            panel = Panel(
                text,
                border_style=COLOR_BLUE,
                box=ROUNDED,
                padding=(0, 1),
                title="[bold cyan]Session Context[/bold cyan]",
            )
            self.console.print(panel)
        else:
            print("\n--- Context ---")
            for k, v in context.items():
                print(f"  {k}: {v}")
