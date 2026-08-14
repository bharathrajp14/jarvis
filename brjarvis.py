#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brjarvis.py — BRJARVIS Global Unified Command Line Tool & Entry Point
=====================================================================
Supports:
  brjarvis ask "What is quantum computing?"
  brjarvis "Tell me a joke"
  brjarvis voice
  brjarvis cli
  brjarvis web
  brjarvis floating
  brjarvis status
  brjarvis doctor
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def main() -> int:
    args = sys.argv[1:]
    if not args:
        # Launch interactive start menu
        from start import main as start_main
        start_main()
        return 0

    first_cmd = args[0].lower().strip().lstrip("-")

    if first_cmd in ("voice", "gui", "hud"):
        from start import launch_voice
        launch_voice()
        return 0

    if first_cmd in ("cli", "terminal", "repl"):
        from start import launch_cli
        launch_cli()
        return 0

    if first_cmd in ("web", "webserver", "server"):
        from start import launch_web_server
        launch_web_server()
        return 0

    if first_cmd in ("float", "floating", "overlay"):
        from start import launch_floating_voice
        launch_floating_voice()
        return 0

    if first_cmd in ("status", "health"):
        from start import show_status
        show_status()
        return 0

    if first_cmd in ("doctor", "fix"):
        from start import doctor
        doctor()
        return 0

    # One-shot query mode: e.g. brjarvis ask "query" or brjarvis "query"
    query_terms = args[1:] if first_cmd == "ask" else args
    query_text = " ".join(query_terms).strip()

    if not query_text:
        if HAS_RICH and console:
            console.print("[yellow]Usage: brjarvis ask \"<question>\" or brjarvis voice | cli | web | floating | status[/yellow]")
        else:
            print("Usage: brjarvis ask \"<question>\" or brjarvis voice | cli | web | floating | status")
        return 1

    if HAS_RICH and console:
        console.print(f"[bold cyan]⚡ BRJARVIS Querying:[bold cyan] [dim]{query_text}[/dim]")

    try:
        from core.bootstrap import build_assistant_runtime
        if HAS_RICH and console:
            with console.status("[bold cyan]BRJARVIS Thinking...[/bold cyan]"):
                runtime = build_assistant_runtime()
                response = runtime.orchestrator.chat(query_text)
                if asyncio.iscoroutine(response):
                    response = asyncio.run(response)
            console.print("\n[bold green]BRJARVIS Response:[/bold green]")
            console.print(Markdown(str(response)))
        else:
            runtime = build_assistant_runtime()
            response = runtime.orchestrator.chat(query_text)
            if asyncio.iscoroutine(response):
                response = asyncio.run(response)
            print(f"\nBRJARVIS: {response}")
    except Exception as e:
        if HAS_RICH and console:
            console.print(f"[bold red]❌ BRJARVIS Execution Error:[bold red] {e}")
        else:
            print(f"BRJARVIS Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
