# src/brjarvis/apps/bootstrap.py — Canonical Application Bootstrap Engine for BR JARVIS MK40.2+
from __future__ import annotations

import atexit
import importlib
import json
import logging
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TextIO, Tuple, TypedDict, cast

from brjarvis.core.paths import paths
from brjarvis.core.version import VERSION, BUILD, CODENAME

# Ensure environment variables from .env are loaded immediately
if paths.DOTENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(paths.DOTENV_FILE)
    except ImportError:
        pass

from brjarvis.diagnostics.doctor import check_module, auto_install_package, run_diagnostics_audit

PYTHON = sys.executable
BASE_DIR = paths.PROJECT_ROOT
LOG_DIR = paths.LOG_ROOT
PID_FILE = paths.PID_FILE

# Setup Rich formatting
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.text import Text
    console = Console()
except ImportError:
    print("Notice: 'rich' module is missing. Running in basic console mode.")
    class DummyConsole:
        def print(self, *args, **kwargs):
            print(*args)
        def clear(self):
            pass
    console = DummyConsole()  # type: ignore


def _cleanup_pid_file():
    try:
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


atexit.register(_cleanup_pid_file)


def banner():
    console.clear()
    now = datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")
    text = Text(justify="center")
    text.append("⚡ BR JARVIS — ADVANCED AI OPERATING SYSTEM ⚡\n", style="bold cyan")
    text.append("Autonomous Cognitive Agent Architecture & Isolated Sandbox Lifecycle Engine\n\n", style="dim")
    text.append(f"Version: {VERSION}  │  Build: {BUILD}  │  Codename: {CODENAME}\n", style="bold green")
    text.append(f"Python: {sys.version.split()[0]}  │  Platform: {platform.system()}  │  Security: FAIL-CLOSED 🛡️\n", style="cyan")
    text.append(now, style="dim")

    panel = Panel(text, border_style="bold cyan", padding=(0, 2))
    console.print(panel)
    console.print()


def show_status():
    banner()
    rep = run_diagnostics_audit(auto_repair=False)

    # Environment
    table_env = Table(title="Environment & Architecture", title_style="bold magenta", show_header=False, box=None)
    table_env.add_column("Property", style="bold")
    table_env.add_column("Value")
    table_env.add_row("Project Root", str(paths.PROJECT_ROOT))
    table_env.add_row("Source Root", str(paths.SOURCE_ROOT))
    table_env.add_row("Runtime Root", str(paths.RUNTIME_ROOT))
    table_env.add_row("Workspace Root", str(paths.WORKSPACE_ROOT))
    table_env.add_row("Python Executable", sys.executable)
    venv = hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    table_env.add_row("Virtual Env", f"[green]Active ({paths.VENV_DIR})[/]" if venv else "[yellow]Not detected[/]")
    
    health_val = rep['overall_health']
    health_style = "bold green" if health_val == "HEALTHY" else ("bold red" if "FAILED" in health_val else "bold yellow")
    table_env.add_row("Overall Health", f"[{health_style}]{health_val}[/]")

    # Backends
    table_be = Table(title="AI Backends & Gateway Routing", title_style="bold magenta", show_header=False, box=None)
    has_any = False
    for label, ok in rep["api_keys"].items():
        table_be.add_row(f"[green]✓ {label}[/]" if ok else f"[dim]○ {label}[/]", "[green]Configured[/]" if ok else "[dim]Not Configured[/]")
        if ok:
            has_any = True

    # Subsystems
    table_sys = Table(title="Subsystems & Registries", title_style="bold magenta", show_header=False, box=None)
    for name, status_text in rep["subsystems_status"].items():
        table_sys.add_row(f"[green]✓ {name}[/]", status_text)

    console.print(table_env)
    console.print()
    if not has_any:
        console.print("[bold yellow]⚠ No backends configured. Add keys to .env[/]")
    console.print(table_be)
    console.print()
    console.print(table_sys)
    console.print()


def show_doctor(rep: Optional[DoctorReport] = None):
    if rep is None:
        rep = run_diagnostics_audit(auto_repair=False)
    show_status()

    # Detailed Python Packages Table
    table_pkg = Table(title="Python Runtime Packages", title_style="bold cyan")
    table_pkg.add_column("Package", style="bold")
    table_pkg.add_column("Status")
    table_pkg.add_column("Version / Details")
    for pkg, (ok, ver) in rep["python_packages"].items():
        table_pkg.add_row(pkg, "[green]Installed[/]" if ok else "[red]Missing[/]", ver)

    # Detailed System Tools Table
    table_tools = Table(title="System & Binary Tools", title_style="bold cyan")
    table_tools.add_column("Category", style="bold")
    table_tools.add_column("Binary")
    table_tools.add_column("Status")
    for cat, found in rep["system_tools"].items():
        table_tools.add_row(cat, found or "N/A", "[green]Available[/]" if found else "[yellow]Not Found[/]")

    console.print(table_pkg)
    console.print()
    console.print(table_tools)
    console.print()


def launch_cli():
    console.print("\n[bold cyan]▶ Starting CLI Orchestrator[/]")
    console.print("[dim]Type /quit to exit.[/]\n")
    from brjarvis.core.cli import run_cli
    run_cli()


def launch_web_server(open_url: Optional[str] = None):
    port = int(os.environ.get("PORT", os.environ.get("BR_SERVER_PORT", "8000")))
    target_url = open_url or f"http://127.0.0.1:{port}"
    console.print("\n[bold cyan]▶ Starting BR Web Core Server[/]")
    console.print(f"  [green]Server Running on[/] http://127.0.0.1:{port}")
    console.print(f"  [green]Interface URL[/] Access [cyan]{target_url}[/]")
    console.print("[dim]Press Ctrl+C to shut down.[/]\n")

    import uvicorn
    from apps.web.api.app import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


def launch_career_studio(open_url: Optional[str] = None):
    port = int(os.environ.get("PORT", os.environ.get("BR_SERVER_PORT", "8000")))
    target_url = open_url or f"http://127.0.0.1:{port}/career"
    launch_web_server(open_url=target_url)


def launch_voice():
    console.print("\n[bold cyan]▶ Starting BR Voice Assistant Cyberpunk HUD[/]")
    try:
        from brjarvis.desktop.ui_mark import run_voice_ui
        run_voice_ui()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Error launching Voice Assistant: {e}[/]")


def main() -> int:
    """Canonical Application Bootstrap CLI Dispatcher."""
    args = sys.argv[1:]
    if not args:
        show_status()
        return 0

    cmd = args[0].lower().strip().lstrip("-")
    if cmd in ("status", "info"):
        show_status()
    elif cmd in ("doctor", "check"):
        auto_fix = "--fix" in args or "-f" in args
        rep = run_diagnostics_audit(auto_repair=auto_fix)
        show_doctor(rep)
    elif cmd in ("cli", "repl", "terminal"):
        launch_cli()
    elif cmd in ("web", "server", "dashboard"):
        launch_web_server()
    elif cmd in ("career", "careeros", "career-os", "studio"):
        launch_career_studio()
    elif cmd in ("sync", "career-sync"):
        from brjarvis.career.crm.database import get_career_crm_db
        db = get_career_crm_db()
        console.print(f"[green]Career CRM synchronized. Total applications: {len(db.list_applications())}[/]")
    elif cmd in ("voice", "hud"):
        launch_voice()
    else:
        # Default to CLI asking question or executing query
        from brjarvis.core.cli import run_query
        return run_query(" ".join(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
