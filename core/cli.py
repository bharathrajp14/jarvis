# core/cli.py — Modern Canonical Interactive CLI REPL for BR JARVIS
from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, Optional

from core.runtime import ApplicationRuntime, get_runtime

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

if sys.platform != "win32":
    try:
        import readline  # noqa: F401
    except ImportError:
        pass

logger = logging.getLogger("JARVIS.CLI")


def print_banner() -> None:
    if HAS_RICH and console:
        console.clear()
        panel = Panel(
            "[bold cyan]⚡ BR JARVIS — Autonomous Personal AI Runtime ⚡[/bold cyan]\n"
            "[dim]Cognitive Multi-Modal Operating Environment[/dim]\n\n"
            "[bold green]Commands:[/] /help, /status, /mode <name>, /clear, /quit",
            border_style="cyan",
            title="[bold yellow]JARVIS CLI[/bold yellow]",
            padding=(0, 2),
        )
        console.print(panel)
        console.print()
    else:
        print("============================================================")
        print(" BR JARVIS — Autonomous Personal AI Runtime ")
        print("============================================================")
        print(" Commands: /help, /status, /mode <name>, /clear, /quit")
        print("============================================================")


def handle_slash_command(cmd: str, runtime: ApplicationRuntime) -> bool:
    """Process interactive slash commands. Returns False if exit requested."""
    parts = cmd.strip().split()
    if not parts:
        return True

    action = parts[0].lower()
    if action in {"/quit", "/exit", "quit", "exit"}:
        return False

    if action == "/help":
        if HAS_RICH and console:
            console.print("[bold yellow]Available CLI Slash Commands:[/bold yellow]")
            console.print("  [cyan]/help[/cyan]          - Show this command reference")
            console.print("  [cyan]/status[/cyan]        - Display active model gateway & runtime health")
            console.print("  [cyan]/mode <name>[/cyan]  - Switch agent profile (recon, coder, analyst, general)")
            console.print("  [cyan]/clear[/cyan]         - Clear terminal console screen")
            console.print("  [cyan]/quit[/cyan]          - Exit CLI cleanly")
        else:
            print("Commands: /help, /status, /mode <name>, /clear, /quit")
        return True

    if action == "/clear":
        if HAS_RICH and console:
            console.clear()
        else:
            print("\033[H\033[J", end="")
        return True

    if action == "/status":
        health = runtime.health.get_status() if hasattr(runtime, "health") else {"status": "ONLINE"}
        if HAS_RICH and console:
            console.print(f"[bold green]✓ Subsystem Status:[/] {health}")
        else:
            print(f"[Status] {health}")
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


def run_cli(runtime: Optional[ApplicationRuntime] = None) -> None:
    """Run the interactive CLI loop."""
    app_runtime = runtime or get_runtime()
    orchestrator = app_runtime.orchestrator

    print_banner()

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
            if not handle_slash_command(user_input, app_runtime):
                if HAS_RICH and console:
                    console.print("[bold yellow]Exiting JARVIS CLI.[/bold yellow]")
                else:
                    print("Exiting CLI.")
                break
            continue

        try:
            if HAS_RICH and console:
                with console.status("[bold cyan]JARVIS Thinking...[/bold cyan]"):
                    reply = orchestrator.chat(user_input)
                    if asyncio.iscoroutine(reply):
                        reply = asyncio.run(reply)
                console.print("\n[bold green]jarvis>[/bold green]")
                if isinstance(reply, str):
                    console.print(reply)
                elif hasattr(reply, "text"):
                    console.print(reply.text)
                else:
                    console.print(str(reply))
            else:
                reply = orchestrator.chat(user_input)
                if asyncio.iscoroutine(reply):
                    reply = asyncio.run(reply)
                print(f"\njarvis> {reply}")
        except Exception as e:
            logger.exception("Error processing CLI input: %s", e)
            if HAS_RICH and console:
                console.print(f"[bold red]Error:[/] {e}")
            else:
                print(f"Error: {e}")


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
