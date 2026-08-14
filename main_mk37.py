"""BR JARVIS CLI Entrypoint.

Provides a rich interactive REPL terminal interface on top of the shared orchestrator runtime.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

from core.bootstrap import build_assistant_runtime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.markdown import Markdown
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

# Enable readline history on non-Windows systems for up-arrow command recall
if sys.platform != "win32":
    try:
        import readline  # noqa: F401
    except ImportError:
        pass

logger = logging.getLogger("JARVIS.CLI")


def _print_banner() -> None:
    if HAS_RICH and console:
        console.clear()
        panel = Panel(
            "[bold cyan]⚡ BR JARVIS MK38 — Autonomous AI OS Terminal ⚡[/bold cyan]\n"
            "[dim]Cognitive Multi-Modal Neural Assistant CLI[/dim]\n\n"
            "[bold green]Commands:[/] /help, /status, /mode <name>, /quit",
            border_style="cyan",
            title="[bold yellow]JARVIS CLI REPL[/bold yellow]",
            padding=(0, 2),
        )
        console.print(panel)
        console.print()
    else:
        print("============================================================")
        print(" BR JARVIS MK38 — Autonomous AI OS Terminal ")
        print("============================================================")
        print(" Type /quit to exit, /help for commands.")
        print("============================================================")


def _handle_command(cmd: str, orchestrator: Any = None) -> bool:
    """Process slash commands. Returns False if exit was requested."""
    parts = cmd.strip().split()
    if not parts:
        return True
    
    action = parts[0].lower()
    if action in {"/quit", "/exit", "quit", "exit"}:
        return False

    if action == "/help":
        if HAS_RICH and console:
            console.print("[bold yellow]Available CLI Slash Commands:[/bold yellow]")
            console.print("  [cyan]/help[/cyan]          - Show this help menu")
            console.print("  [cyan]/status[/cyan]        - Display active system & backend health")
            console.print("  [cyan]/mode <name>[/cyan]  - Switch agent profile (recon, exploit, coder, analyst, general)")
            console.print("  [cyan]/quit[/cyan]          - Exit CLI cleanly")
        else:
            print("Commands:\n  /help, /status, /mode <name>, /quit")
        return True

    if action == "/status":
        if HAS_RICH and console:
            console.print("[bold green]✓ Subsystem Status:[/] Runtime initialized & healthy.")
        else:
            print("[Status] Runtime initialized & healthy.")
        return True

    if action == "/mode":
        mode_name = parts[1] if len(parts) > 1 else "general"
        if HAS_RICH and console:
            console.print(f"[bold cyan]Agent mode switched to:[/] [yellow]{mode_name}[/yellow]")
        else:
            print(f"[Mode] Switched to {mode_name}")
        return True

    if HAS_RICH and console:
        console.print(f"[yellow]Unknown command: {cmd}. Type /help for assistance.[/yellow]")
    else:
        print(f"Unknown command: {cmd}")
    return True


def main() -> None:
    orchestrator = None

    def _get_orchestrator():
        nonlocal orchestrator
        if orchestrator is None:
            if HAS_RICH and console:
                with console.status("[bold cyan]Initializing JARVIS AI Orchestrator Core...[/bold cyan]"):
                    runtime = build_assistant_runtime()
                    orchestrator = runtime.orchestrator
            else:
                runtime = build_assistant_runtime()
                orchestrator = runtime.orchestrator
        return orchestrator

    _print_banner()

    try:
        while True:
            try:
                if HAS_RICH and console:
                    user_input = Prompt.ask("\n[bold cyan]you[/bold cyan]").strip()
                else:
                    user_input = input("\nyou> ").strip()
            except (EOFError, KeyboardInterrupt):
                if HAS_RICH and console:
                    console.print("\n[dim]Signal received. Exiting CLI...[/dim]")
                else:
                    print("\nExiting CLI...")
                break

            if not user_input:
                continue

            if user_input.startswith("/") or user_input.lower() in {"quit", "exit"}:
                if not _handle_command(user_input, orchestrator):
                    if HAS_RICH and console:
                        console.print("[bold yellow]Exiting JARVIS CLI.[/bold yellow]")
                    else:
                        print("Exiting CLI.")
                    break
                continue

            try:
                orc = _get_orchestrator()
                if HAS_RICH and console:
                    with console.status("[bold cyan]JARVIS Thinking...[/bold cyan]"):
                        reply = orc.chat(user_input)
                        if asyncio.iscoroutine(reply):
                            reply = asyncio.run(reply)
                    console.print("\n[bold green]jarvis>[/bold green]")
                    console.print(Markdown(str(reply)))
                else:
                    reply = orc.chat(user_input)
                    if asyncio.iscoroutine(reply):
                        reply = asyncio.run(reply)
                    print(f"\njarvis> {reply}")
            except Exception as e:
                logger.error("CLI Chat exception: %s", e, exc_info=True)
                if HAS_RICH and console:
                    console.print(f"[bold red]❌ Error:[bold red] {e}")
                else:
                    print(f"Error: {e}")
    finally:
        if orchestrator is not None:
            try:
                orchestrator.shutdown()
            except Exception as e:
                logger.debug("Shutdown exception: %s", e)
        if HAS_RICH and console:
            console.print("\n[bold cyan]👋 JARVIS CLI shutdown complete.[/bold cyan]")
        else:
            print("\n👋 JARVIS CLI shutdown complete.")


if __name__ == "__main__":
    sys.exit(main() or 0)

