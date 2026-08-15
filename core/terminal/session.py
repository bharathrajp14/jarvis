# core/terminal/session.py — Interactive Agent Terminal Session Controller for BR JARVIS
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

from core.runtime import ApplicationRuntime, get_runtime
from core.terminal.commands import SlashCommandHandler, VALID_MODES
from core.terminal.renderer import TerminalRenderer
from core.terminal.theme import (
    COLOR_AMBER,
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_MAGENTA,
    COLOR_RED,
    Glyphs,
    MODE_COLORS,
)
from core.version import BUILD, CODENAME, VERSION

try:
    from rich.prompt import Prompt
    from rich.live import Live
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.status import Status
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

logger = logging.getLogger("JARVIS.TerminalSession")


class TerminalSession:
    """Master CLI Terminal Session Controller.
    
    Manages user interaction, REPL lifecycle, live streaming execution,
    tool call visualization, and event telemetry.
    """

    def __init__(
        self,
        runtime: Optional[ApplicationRuntime] = None,
        *,
        mode: str = "general",
        session_id: Optional[str] = None,
        auto_welcome: bool = True,
    ):
        self.runtime: ApplicationRuntime = runtime or get_runtime()
        self.orchestrator = self.runtime.orchestrator
        self.renderer: TerminalRenderer = TerminalRenderer()
        self.commands: SlashCommandHandler = SlashCommandHandler(self)
        
        self.session_id: str = session_id or getattr(self.orchestrator, "session_id", str(uuid.uuid4()))
        self.current_mode: str = mode if mode in VALID_MODES else "general"
        if self.orchestrator:
            self.orchestrator.current_mode = self.current_mode
            
        self.auto_welcome: bool = auto_welcome
        self._is_running: bool = False
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Subscribe to event bus for real-time background task updates."""
        try:
            event_bus = self.runtime.event_bus
            if event_bus:
                event_bus.subscribe("task.completed", self._on_task_event)
                event_bus.subscribe("task.failed", self._on_task_event)
        except Exception as e:
            logger.debug("EventBus listener setup notice: %s", e)

    def _on_task_event(self, event: Any) -> None:
        """Handle background task notifications asynchronously."""
        try:
            status = getattr(event, "status", "updated")
            goal = getattr(event, "goal", "")
            if goal and self._is_running:
                pass  # Telemetry available if needed
        except Exception:
            pass

    def render_header(self) -> None:
        """Render session status header."""
        info = {
            "mode": self.current_mode,
            "model": getattr(self.runtime.config.models, "default_backend", "Gemini 2.5 Flash") if hasattr(self.runtime, "config") else "Gemini",
            "session_id": self.session_id,
            "permission_mode": os.environ.get("JARVIS_PERMISSION_MODE", "FAIL-CLOSED"),
            "memory_status": "ACTIVE",
        }
        self.renderer.render_header(info)

    def get_prompt_text(self) -> str:
        """Format the interactive user prompt string."""
        mode_color = MODE_COLORS.get(self.current_mode, "cyan")
        if HAS_RICH:
            return f"\n[bold white]you[/bold white] [{mode_color} bold]({self.current_mode.upper()})[/] [cyan]>[/] "
        return f"\nyou ({self.current_mode.upper()})> "

    def run_repl(self) -> None:
        """Start interactive REPL loop."""
        self._is_running = True
        self.renderer.clear()
        self.render_header()
        
        if self.auto_welcome:
            self.renderer.render_welcome()

        while self._is_running:
            try:
                prompt_str = self.get_prompt_text()
                if HAS_RICH:
                    user_input = Prompt.ask(prompt_str).strip()
                else:
                    user_input = input(prompt_str).strip()
            except (EOFError, KeyboardInterrupt):
                if HAS_RICH and self.renderer.console:
                    self.renderer.console.print("\n[dim]Exiting JARVIS Terminal Agent...[/dim]")
                else:
                    print("\nExiting JARVIS Terminal Agent...")
                break

            if not user_input:
                continue

            # Process slash commands
            if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
                should_continue = self.commands.execute(user_input)
                if not should_continue:
                    break
                continue

            # Execute cognitive turn
            self.execute_turn(user_input)

        self._is_running = False

    def execute_turn(self, user_input: str) -> None:
        """Execute a cognitive agent turn with live tool visualization and response streaming."""
        t_start = time.monotonic()
        
        try:
            if HAS_RICH and self.renderer.console and getattr(sys.stdout, "isatty", lambda: False)():
                with self.renderer.console.status(
                    f"[bold cyan]JARVIS Thinking...[/bold cyan] [dim]({self.current_mode.upper()} mode)[/dim]",
                    spinner="dots"
                ):
                    response = self.orchestrator.chat(user_input)
                    if asyncio.iscoroutine(response):
                        response = asyncio.run(response)
            else:
                response = self.orchestrator.chat(user_input)
                if asyncio.iscoroutine(response):
                    response = asyncio.run(response)

            elapsed_ms = (time.monotonic() - t_start) * 1000

            # Render response
            self._render_turn_output(user_input, response, elapsed_ms)

        except KeyboardInterrupt:
            if HAS_RICH and self.renderer.console:
                self.renderer.console.print("\n[bold yellow]⚠ Turn interrupted by user (Ctrl+C). Ready for next instruction.[/bold yellow]")
            else:
                print("\n[Turn interrupted by user]")
        except Exception as e:
            logger.exception("Error executing agent turn: %s", e)
            self.renderer.render_error("Agent Execution Error", str(e), [
                "Verify your API keys in .env (GEMINI_API_KEY, OPENAI_API_KEY)",
                "Try running /doctor to diagnose subsystem health",
                "Try switching agent mode via /mode coder or /mode general"
            ])

    def _render_turn_output(self, user_input: str, response: Any, elapsed_ms: float) -> None:
        """Render final response and any generated artifacts or tool verification evidence."""
        if HAS_RICH and self.renderer.console:
            mode_color = MODE_COLORS.get(self.current_mode, "cyan")
            self.renderer.console.print(f"\n[{mode_color} bold]jarvis[/] [dim]({elapsed_ms:.0f}ms)[/]:")
            
            resp_str = str(response) if not hasattr(response, "text") else response.text
            self.renderer.render_markdown(resp_str)
            self.renderer.console.print()
        else:
            print(f"\njarvis ({elapsed_ms:.0f}ms):\n{response}\n")

    def run_query(self, query: str) -> int:
        """Execute a single one-shot query and exit cleanly."""
        self.render_header()
        if HAS_RICH and self.renderer.console:
            self.renderer.console.print(f"[bold cyan]⚡ Query:[/] [white]{query}[/]\n")
        else:
            print(f"Query: {query}\n")

        self.execute_turn(query)
        return 0
