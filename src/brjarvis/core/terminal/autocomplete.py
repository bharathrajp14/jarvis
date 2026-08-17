# core/terminal/autocomplete.py — Command Palette & Autocomplete Engine for BR JARVIS MK41
"""
Provides prompt_toolkit-powered interactive autocomplete, command palette,
and persistent command history for the BR JARVIS CLI terminal.

Falls back to readline (or no completion) if prompt_toolkit is unavailable.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, List, Optional

# ── prompt_toolkit availability ───────────────────────────────────────────────
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, WordCompleter
    from prompt_toolkit.history import FileHistory, InMemoryHistory
    from prompt_toolkit.styles import Style as PTStyle
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False
    PromptSession = None  # type: ignore

# ── Slash command registry ────────────────────────────────────────────────────

SLASH_COMMANDS: List[dict] = [
    # Core interaction
    {"cmd": "/help",        "desc": "Show full command reference"},
    {"cmd": "/status",      "desc": "Subsystem health & telemetry"},
    {"cmd": "/clear",       "desc": "Clear terminal screen"},
    {"cmd": "/quit",        "desc": "Exit with memory consolidation"},
    {"cmd": "/version",     "desc": "Show build & version info"},
    # Planning & execution
    {"cmd": "/plan",        "desc": "Decompose goal into a step plan before executing"},
    {"cmd": "/approve",     "desc": "Approve a pending task: /approve <task_id>"},
    {"cmd": "/verify",      "desc": "Run verification on a file or task"},
    {"cmd": "/diff",        "desc": "Show file diff: /diff <filepath>"},
    # Task lifecycle
    {"cmd": "/tasks",       "desc": "Task dashboard: /tasks or /tasks <id>"},
    {"cmd": "/pause",       "desc": "Pause a running task: /pause <task_id>"},
    {"cmd": "/resume",      "desc": "Resume a paused task: /resume <task_id>"},
    {"cmd": "/cancel",      "desc": "Cancel a task: /cancel <task_id>"},
    {"cmd": "/retry",       "desc": "Retry a failed task: /retry <task_id>"},
    {"cmd": "/continue",    "desc": "Resume latest incomplete session or task"},
    # Agent & model
    {"cmd": "/mode",        "desc": "Switch persona: /mode <general|coder|analyst|researcher|planner|automation|recon>"},
    {"cmd": "/model",       "desc": "View or switch AI backend: /model [gemini|claude|gpt|ollama]"},
    {"cmd": "/permission",  "desc": "View or set permission mode: /permission [mode]"},
    # Memory & context
    {"cmd": "/memory",      "desc": "Memory commands: search <q> | recent | project | stats | forget <id>"},
    {"cmd": "/compact",     "desc": "Consolidate working memory into long-term store"},
    {"cmd": "/context",     "desc": "Show current task context, memory, model, services"},
    # Session
    {"cmd": "/session",     "desc": "View active session context or switch: /session [id]"},
    {"cmd": "/sessions",    "desc": "List all active and persisted agent sessions"},
    {"cmd": "/history",     "desc": "View session turns: /history [n] or /history task <id>"},
    {"cmd": "/rename",      "desc": "Name current session: /rename <name>"},
    {"cmd": "/export",      "desc": "Export session transcript: /export [markdown|json]"},
    # Tools, skills & infrastructure
    {"cmd": "/tools",       "desc": "Browse tools: /tools [search <q>] [health] [failed]"},
    {"cmd": "/skills",      "desc": "Browse extensible skills and workflows: /skills [query]"},
    {"cmd": "/connectors",  "desc": "Connector status: /connectors or /connectors <name>"},
    {"cmd": "/config",      "desc": "Show runtime environment & provider configuration"},
    {"cmd": "/doctor",      "desc": "Run interactive system diagnostics"},
    {"cmd": "/usage",       "desc": "Show token & request usage stats"},
    {"cmd": "/interrupt",   "desc": "Safely interrupt and preserve active agent task"},
    # Output style & interactions
    {"cmd": "/style",       "desc": "Set output style: /style [compact|detailed|minimal|verbose]"},
    {"cmd": "/verbose",     "desc": "Toggle verbose debug output: /verbose [on|off]"},
    {"cmd": "/mouse",       "desc": "Configure mouse modes: /mouse [on|off|scroll|interactive|full|status]"},
    {"cmd": "/tui",         "desc": "Toggle fullscreen TUI mode: /tui [fullscreen|default]"},
    # Career OS
    {"cmd": "/career",      "desc": "Career profile & funnel analytics"},
    {"cmd": "/applications","desc": "List tracked job applications"},
    {"cmd": "/interviews",  "desc": "List upcoming interviews"},
    {"cmd": "/offers",      "desc": "List job offers"},
    {"cmd": "/emails",      "desc": "Career email intelligence feed"},
    {"cmd": "/resume",      "desc": "Generate or tailor resume"},
    {"cmd": "/jobs",        "desc": "Search and match job postings"},
    {"cmd": "/apply",       "desc": "Prepare application package: /apply <job_id>"},
    {"cmd": "/ats",         "desc": "Run ATS audit: /ats [role]"},
]

# Mode choices
VALID_MODES = ["general", "coder", "analyst", "recon", "exploit", "report", "planner", "researcher", "automation"]

# Model choices
VALID_MODELS = ["gemini", "claude", "gpt", "mistral", "ollama", "gateway"]

# Permission modes
VALID_PERMISSIONS = ["auto", "plan", "accept_edits", "confirm_destructive", "confirm_all", "deny"]

# Style choices
VALID_STYLES = ["compact", "detailed", "minimal", "verbose"]


class JarvisCompleter:
    """Smart completer for BR JARVIS CLI commands."""

    def __init__(self):
        self._cmd_names = [c["cmd"] for c in SLASH_COMMANDS]

    def get_completions_for(self, text: str) -> List[dict]:
        """Return list of completion suggestions for a partial input string."""
        stripped = text.lstrip()
        if not stripped.startswith("/"):
            return []

        parts = stripped.split(maxsplit=1)
        cmd_part = parts[0]
        arg_part = parts[1].strip() if len(parts) > 1 else ""

        # Argument-level completions
        if len(parts) > 1:
            if cmd_part == "/mode":
                return [{"text": m, "desc": f"Switch to {m} mode"} for m in VALID_MODES if m.startswith(arg_part)]
            if cmd_part == "/model":
                return [{"text": m, "desc": f"Use {m} backend"} for m in VALID_MODELS if m.startswith(arg_part)]
            if cmd_part == "/permission":
                return [{"text": p, "desc": ""} for p in VALID_PERMISSIONS if p.startswith(arg_part)]
            if cmd_part == "/style":
                return [{"text": s, "desc": ""} for s in VALID_STYLES if s.startswith(arg_part)]
            if cmd_part == "/memory":
                subs = ["search", "recent", "project", "stats", "forget"]
                return [{"text": s, "desc": ""} for s in subs if s.startswith(arg_part)]
            if cmd_part == "/tools":
                subs = ["health", "failed", "search"]
                return [{"text": s, "desc": ""} for s in subs if s.startswith(arg_part)]
            if cmd_part == "/verbose":
                return [{"text": o, "desc": ""} for o in ["on", "off"] if o.startswith(arg_part)]
            if cmd_part == "/mouse":
                subs = ["on", "off", "scroll", "interactive", "full", "status"]
                return [{"text": s, "desc": f"Set mouse capture mode: {s}"} for s in subs if s.startswith(arg_part)]
            if cmd_part == "/tui":
                subs = ["fullscreen", "default"]
                return [{"text": s, "desc": f"Switch TUI mode: {s}"} for s in subs if s.startswith(arg_part)]
            return []

        # Command-level completions
        q = cmd_part.lower()
        matches = []
        for c in SLASH_COMMANDS:
            if c["cmd"].startswith(q):
                matches.append({"text": c["cmd"], "desc": c["desc"]})
        return matches


# ── prompt_toolkit Completer bridge ──────────────────────────────────────────

if HAS_PROMPT_TOOLKIT:
    class PTJarvisCompleter(Completer):  # type: ignore
        """prompt_toolkit Completer for BR JARVIS slash commands."""

        def __init__(self):
            self._engine = JarvisCompleter()

        def get_completions(self, document, complete_event):  # type: ignore
            text = document.text_before_cursor
            suggestions = self._engine.get_completions_for(text)
            for s in suggestions:
                yield Completion(
                    s["text"],
                    start_position=-len(text.lstrip()),
                    display_meta=s.get("desc", ""),
                )


def get_history_path() -> Path:
    """Locate CLI command history file."""
    try:
        from brjarvis.core.paths import paths
        history_dir = paths.STATE_ROOT / "cli"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir / "command_history.txt"
    except Exception:
        return Path.home() / ".brjarvis_history"


def get_prompt_toolkit_style() -> Any:
    """Return a prompt_toolkit Style matching the BR JARVIS color palette."""
    if not HAS_PROMPT_TOOLKIT:
        return None
    return PTStyle.from_dict({
        "prompt.you":                                 "#00e5ff bold",
        "prompt.bracket":                             "#48586c",
        "prompt.mode":                                "#1de9b6 bold",
        "prompt.arrow":                               "#00e5ff bold",
        "prompt.task":                                "#1de9b6 bold",
        "prompt.approval":                            "#ffab00 bold",
        "prompt.needs":                               "#d500f9 bold",
        # Auto-completion menu
        "completion-menu":                            "bg:#10141d #f0f6fc",
        "completion-menu.completion":                 "bg:#151b26 #00e5ff",
        "completion-menu.completion.current":         "bg:#253346 #ffffff bold",
        "completion-menu.meta.completion":            "bg:#151b26 #6b7d96",
        "completion-menu.meta.completion.current":    "bg:#253346 #1de9b6",
        "completion-menu.multi-column-meta":          "bg:#151b26 #6b7d96",
        "scrollbar.background":                       "bg:#151b26",
        "scrollbar.button":                           "bg:#00e5ff",
        # Auto-suggestions
        "auto-suggest":                               "#48586c italic",
    })


def build_prompt_session(
    history_path: Optional[Path] = None,
    mouse_support: bool = False,
) -> Any:
    """Build and return a prompt_toolkit PromptSession (or None if unavailable)."""
    if not HAS_PROMPT_TOOLKIT:
        return None

    # Check env var override if not explicitly provided
    env_mouse = os.environ.get("JARVIS_MOUSE_SUPPORT", "0").strip().lower()
    effective_mouse = mouse_support or (env_mouse in ("1", "true", "yes", "on", "enable", "enabled"))

    hist_path = history_path or get_history_path()
    try:
        history = FileHistory(str(hist_path))
    except Exception:
        history = InMemoryHistory()  # type: ignore

    # Keyboard bindings: Esc & Ctrl+C for interrupt and clearing
    kb = KeyBindings()

    @kb.add("escape")
    def _on_escape(event: Any) -> None:
        """Handle Esc key: dismiss completion menu, clear current buffer, or trigger interrupt."""
        buf = event.current_buffer
        if buf.complete_state:
            buf.cancel_completion()
        elif buf.text:
            buf.reset()
        else:
            event.app.exit(exception=KeyboardInterrupt("Interrupted with Escape key"))

    @kb.add("c-c")
    def _on_ctrl_c(event: Any) -> None:
        """Handle Ctrl+C: cancel input or interrupt."""
        event.app.exit(exception=KeyboardInterrupt("Interrupted with Ctrl+C"))

    session = PromptSession(
        history=history,
        completer=PTJarvisCompleter(),
        auto_suggest=AutoSuggestFromHistory(),
        style=get_prompt_toolkit_style(),
        enable_system_prompt=False,
        mouse_support=effective_mouse,
        reserve_space_for_menu=4,
        key_bindings=kb,
    )
    return session


__all__ = [
    "HAS_PROMPT_TOOLKIT",
    "JarvisCompleter",
    "SLASH_COMMANDS",
    "VALID_MODES",
    "VALID_MODELS",
    "VALID_PERMISSIONS",
    "VALID_STYLES",
    "build_prompt_session",
    "get_prompt_toolkit_style",
    "get_history_path",
]
