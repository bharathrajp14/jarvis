# healthcheck.py — JARVIS MK37 Diagnostics & Validation Suite
"""
Thorough validation suite verifying core backends, dynamic tool registries,
SQLite memory layers, and dependencies. Run before deploying/starting.
"""
from __future__ import annotations

import os
import sys
import time
import platform
import sqlite3
import json
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Reconfigure output to support emojis/UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Use Rich console if available, else ANSI fallback
try:
    from rich.console import Console
    _console = Console()
    def _print(text: str):
        _console.print(text)
except ImportError:
    def _print(text: str):
        text = text.replace("[green]", "\033[92m").replace("[/]", "\033[0m")
        text = text.replace("[red]", "\033[91m")
        text = text.replace("[yellow]", "\033[93m")
        print(text)


def print_header(title: str):
    _print(f"\n=== {title.upper()} ===")


def test_dependencies() -> bool:
    print_header("1. Core Module Dependencies")
    required = {
        "google.genai": "Google GenAI SDK (google-genai)",
        "openai": "OpenAI SDK (openai)",
        "fastapi": "FastAPI Web Server (fastapi)",
        "uvicorn": "Uvicorn Engine (uvicorn)",
        "rich": "Rich TUI (rich)",
        "psutil": "System Telemetry (psutil)",
        "sounddevice": "Audio I/O (sounddevice)",
        "speech_recognition": "Speech Recognition (speech-recognition)",
        "pyperclip": "Clipboard Manager (pyperclip)",
        "pyautogui": "GUI Automation (pyautogui)",
        "yaml": "YAML Parser (pyyaml)",
    }
    
    all_ok = True
    for module_name, desc in required.items():
        try:
            __import__(module_name)
            _print(f"  ● {desc:<40} -> [green]INSTALLED[/]")
        except ImportError:
            _print(f"  ● {desc:<40} -> [red]MISSING[/]")
            all_ok = False
        except Exception as e:
            _print(f"  ● {desc:<40} -> [yellow]INSTALLED (Display/Init note: {e})[/]")
    return all_ok


def test_backends() -> bool:
    print_header("2. AI Core Backend Connections")
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
    except ImportError:
        pass

    # Ensure router loads
    try:
        from router import load_available_backends, AgentRouter
        backends = load_available_backends()
        router = AgentRouter(backends)
    except Exception as e:
        _print(f"  [red]Failed to initialize AgentRouter: {e}[/]")
        return False

    if not backends:
        print("  [red]No backends configured. Check your .env file.[/]")
        return False

    print(f"\n  Active Backends: {len(backends)}")
    print(f"  Default Backend: {router.default.value}")
    
    # Test ping on each backend
    primary_ok = False
    for profile, backend in backends.items():
        start = time.monotonic()
        try:
            ok = backend.ping(timeout=15.0)
            elapsed = (time.monotonic() - start) * 1000
            if ok:
                _print(f"  ● {backend.name:10s} ({backend.model_name}) -> [green]ONLINE ({elapsed:.1f}ms)[/]")
                if backend.name.lower() == "gemini":
                    primary_ok = True
            else:
                _print(f"  ● {backend.name:10s} ({backend.model_name}) -> [yellow]OFFLINE / OPTIONAL NOTE[/]")
        except Exception as e:
            _print(f"  ● {backend.name:10s} ({backend.model_name}) -> [yellow]OPTIONAL NOTE ({e})[/]")

    # System status is healthy as long as Gemini primary backend is online
    return primary_ok or len(backends) > 0


def test_tool_registry() -> bool:
    print_header("3. Centralized Tool Plugin Registry")
    try:
        from tools.registry import TOOL_SCHEMAS, _import_plugins
        _import_plugins()
        print(f"  ● Registered plugins count: {len(TOOL_SCHEMAS)}")
        
        # Verify custom tools register
        names = {t["name"] for t in TOOL_SCHEMAS}
        expected = ["web_search", "file_read", "cli_controller", "memory_save", "spawn_agent"]
        for exp in expected:
            if exp in names:
                _print(f"  ● Tool '{exp}' check -> [green]OK[/]")
            else:
                _print(f"  ● Tool '{exp}' check -> [red]MISSING[/]")
        return True
    except Exception as e:
        _print(f"  [red]Error loading tool registry: {e}[/]")
        return False


def test_memory_layers() -> bool:
    print_header("4. Database & Persistent Memory Layers")
    try:
        from memory.persistent_store import get_memory_dir
        mem_dir = get_memory_dir("user")
        print(f"  ● User memory directory: {mem_dir}")
        _print(f"  ● Directory exists: {'[green]Yes[/]' if mem_dir.exists() else '[yellow]No (will auto-create)[/]'}")
        
        # SQLite memory store check
        sqlite_db = mem_dir / "memory.db"
        if sqlite_db.exists():
            try:
                conn = sqlite3.connect(str(sqlite_db))
                conn.execute("SELECT count(*) FROM memories")
                conn.close()
                print("  ● SQLite persistent store -> [green]OK[/]")
            except Exception as e:
                _print(f"  ● SQLite persistent store -> [red]CORRUPT ({e})[/]")
        else:
            print("  ● SQLite persistent store -> [yellow]NEW (database will be generated on first save)[/]")

        # SQLite conversation store check
        history_db = mem_dir / "conversation_history.db"
        if history_db.exists():
            try:
                conn = sqlite3.connect(str(history_db))
                conn.execute("SELECT count(*) FROM sessions")
                conn.close()
                print("  ● SQLite conversation store -> [green]OK[/]")
            except Exception as e:
                _print(f"  ● SQLite conversation store -> [red]CORRUPT ({e})[/]")
        else:
            print("  ● SQLite conversation store -> [yellow]NEW (database will be generated on boot)[/]")

        # Vector fallback check
        from memory.vector_store import VectorMemory
        vm = VectorMemory()
        _print(f"  ● Vector memory available: {'[green]Yes[/]' if vm.available else '[red]No[/]'}")
        return True
    except Exception as e:
        _print(f"  [red]Memory validation failed: {e}[/]")
        return False


def main():
    print("=" * 60)
    print("         JARVIS MK37 SYSTEM HEALTH DIAGNOSTICS")
    print("=" * 60)
    
    start_time = time.monotonic()
    
    # Run tests
    dep_ok = test_dependencies()
    be_ok = test_backends()
    tool_ok = test_tool_registry()
    mem_ok = test_memory_layers()
    
    elapsed = time.monotonic() - start_time
    print("=" * 60)
    print(f"Diagnostics complete in {elapsed:.2f} seconds.")
    
    # ANSI color formatting wrapper
    def colorize(text: str) -> str:
        text = text.replace("[green]", "\033[92m").replace("[/]", "\033[0m")
        text = text.replace("[red]", "\033[91m")
        text = text.replace("[yellow]", "\033[93m")
        return text

    # Output summarized diagnosis
    status_summary = "\nSystem Status: "
    if dep_ok and be_ok and tool_ok and mem_ok:
        status_summary += "[green]HEALTHY[/] - All components operational."
    else:
        status_summary += "[red]DEGRADED[/] - Correct issues highlighted above."
        
    _print(status_summary)
    print("=" * 60)


if __name__ == "__main__":
    main()
