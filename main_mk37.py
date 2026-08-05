"""BR JARVIS legacy CLI entrypoint.

This module preserves historical references to main_mk37 while providing a
direct REPL-style CLI on top of the shared orchestrator runtime.

Improvements:
- orchestrator.shutdown() called on clean exit (consolidates memory)
- Signal handling via KeyboardInterrupt properly triggers shutdown
- readline history enabled on non-Windows for up-arrow command recall
"""
from __future__ import annotations

import asyncio
import sys
import os

from core.bootstrap import build_assistant_runtime


# Enable readline history on non-Windows systems for up-arrow command recall
if sys.platform != "win32":
    try:
        import readline  # noqa: F401
    except ImportError:
        pass


def _print_banner() -> None:
    print("=" * 60)
    print(" BR JARVIS MK37 — Autonomous AI OS ")
    print("=" * 60)
    print(" Type /quit to exit, /help for commands.")
    print(" Chat naturally or use /mode <name> to switch modes.")
    print("=" * 60)


def _handle_command(cmd: str) -> bool:
    """Process slash commands. Returns False if exit was requested."""
    low = cmd.strip().lower()
    if low in {"/quit", "/exit", "quit", "exit"}:
        return False
    if low == "/help":
        print("Commands:")
        print("  /help         - Show this help")
        print("  /mode <name>  - Switch mode (recon, exploit, coder, analyst, general)")
        print("  /quit         - Exit CLI cleanly")
        print("  /status       - Show backend status")
        return True
    return True


def main() -> None:
    orchestrator = None

    def _get_orchestrator():
        nonlocal orchestrator
        if orchestrator is None:
            runtime = build_assistant_runtime()
            orchestrator = runtime.orchestrator
        return orchestrator

    _print_banner()

    try:
        while True:
            try:
                user_input = input("you> ").strip()
            except EOFError:
                print("\nEOF received. Exiting CLI.")
                break
            except KeyboardInterrupt:
                print("\n^C detected. Exiting cleanly...")
                break

            if not user_input:
                continue

            if user_input.startswith("/") or user_input.lower() in {"quit", "exit"}:
                if not _handle_command(user_input):
                    print("Exiting CLI.")
                    break
                continue

            try:
                orc = _get_orchestrator()
                reply = orc.chat(user_input)
                if asyncio.iscoroutine(reply):
                    reply = asyncio.run(reply)
                print(f"jarvis> {reply}")
            except Exception as exc:
                print(f"jarvis> [error] {exc}")

    finally:
        # FIXED: Always call shutdown on exit so working memory is consolidated
        # and conversation store receives the end_session record.
        if orchestrator is not None:
            try:
                orchestrator.shutdown()
            except Exception:
                pass
        print("👋 JARVIS shutdown complete.")


if __name__ == "__main__":
    sys.exit(main() or 0)
