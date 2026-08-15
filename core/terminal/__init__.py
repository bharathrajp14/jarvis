# core/terminal/__init__.py — Master Terminal Agent Package for BR JARVIS
from __future__ import annotations

from typing import Optional

from core.runtime import ApplicationRuntime
from core.terminal.commands import SlashCommandHandler, VALID_MODES
from core.terminal.renderer import TerminalRenderer
from core.terminal.session import TerminalSession
from core.terminal.theme import Glyphs, MODE_COLORS, get_terminal_theme


def run_cli(
    runtime: Optional[ApplicationRuntime] = None,
    mode: str = "general",
    session_id: Optional[str] = None,
) -> None:
    """Launch the interactive BR JARVIS CLI Agent REPL."""
    session = TerminalSession(runtime=runtime, mode=mode, session_id=session_id)
    session.run_repl()


def run_query(
    query: str,
    runtime: Optional[ApplicationRuntime] = None,
    mode: str = "general",
) -> int:
    """Execute a one-shot query using the BR JARVIS terminal agent."""
    session = TerminalSession(runtime=runtime, mode=mode, auto_welcome=False)
    return session.run_query(query)


__all__ = [
    "TerminalSession",
    "TerminalRenderer",
    "SlashCommandHandler",
    "Glyphs",
    "MODE_COLORS",
    "VALID_MODES",
    "get_terminal_theme",
    "run_cli",
    "run_query",
]
