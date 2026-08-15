#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brjarvis.py — BRJARVIS Global Unified Command Line Tool & Entry Point
=====================================================================
Supports:
  brjarvis ask "What is quantum computing?"
  brjarvis "Create a snake game in Python" --mode coder
  brjarvis cli
  brjarvis voice
  brjarvis web
  brjarvis floating
  brjarvis status
  brjarvis doctor
"""
from __future__ import annotations

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


def main() -> int:
    args = sys.argv[1:]
    if not args:
        # Launch interactive start menu
        from start import main as start_main
        start_main()
        return 0

    first_cmd = args[0].lower().strip().lstrip("-")

    if first_cmd in ("help", "h"):
        from core.terminal.renderer import TerminalRenderer
        renderer = TerminalRenderer()
        renderer.render_header()
        renderer.render_welcome()
        return 0

    if first_cmd in ("voice", "gui", "hud"):
        from start import launch_voice
        launch_voice()
        return 0

    if first_cmd in ("cli", "terminal", "repl"):
        from core.cli import run_cli
        # Extract optional mode flag if passed
        mode = "general"
        if len(args) > 2 and args[1] in ("-m", "--mode"):
            mode = args[2]
        run_cli(mode=mode)
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

    # Parse flags like --mode
    mode = "general"
    clean_args = []
    i = 0
    while i < len(args):
        if args[i] in ("-m", "--mode") and i + 1 < len(args):
            mode = args[i + 1]
            i += 2
        else:
            clean_args.append(args[i])
            i += 1

    if clean_args and clean_args[0].lower().strip().lstrip("-") == "ask":
        clean_args = clean_args[1:]

    query_text = " ".join(clean_args).strip()

    if not query_text:
        try:
            from rich.console import Console
            Console().print("[yellow]Usage: brjarvis ask \"<question>\" [-m <mode>] or brjarvis cli | voice | web | floating | status | doctor[/yellow]")
        except ImportError:
            print("Usage: brjarvis ask \"<question>\" [-m <mode>] or brjarvis cli | voice | web | floating | status | doctor")
        return 1

    from core.terminal import run_query
    return run_query(query_text, mode=mode)


if __name__ == "__main__":
    sys.exit(main())
