# core/terminal/theme.py — Design System & Visual Tokens for BR JARVIS CLI
from __future__ import annotations

from typing import Dict

try:
    from rich.box import DOUBLE, HEAVY, ROUNDED, SIMPLE, Box
    from rich.style import Style
    from rich.theme import Theme

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    ROUNDED = None
    HEAVY = None
    DOUBLE = None
    SIMPLE = None


# ── Color Palette Tokens ─────────────────────────────────────────────────────
# Cyberpunk Titanium / Deep Space Neo-Interface Palette
COLOR_CYAN = "#00e5ff"
COLOR_GREEN = "#00e676"
COLOR_AMBER = "#ffab00"
COLOR_RED = "#ff1744"
COLOR_MAGENTA = "#d500f9"
COLOR_BLUE = "#2979ff"
COLOR_DARK = "#10141d"
COLOR_PANEL_BG = "#151b26"
COLOR_BORDER = "#253346"
COLOR_DIM = "#6b7d96"
COLOR_WHITE = "#f0f6fc"
COLOR_ORANGE = "#ff6d00"
COLOR_TEAL = "#1de9b6"
COLOR_PURPLE = "#7c4dff"
COLOR_MUTED = "#48586c"

# ── Mode Color Mapping ───────────────────────────────────────────────────────
MODE_COLORS: Dict[str, str] = {
    "general": COLOR_CYAN,
    "coder": COLOR_GREEN,
    "analyst": COLOR_MAGENTA,
    "recon": COLOR_AMBER,
    "exploit": COLOR_RED,
    "report": COLOR_BLUE,
    "planner": COLOR_TEAL,
    "researcher": COLOR_ORANGE,
    "automation": COLOR_CYAN,
}


# ── Glyphs & Symbols ─────────────────────────────────────────────────────────
class Glyphs:
    # Unicode glyphs
    LIGHTNING = "⚡"
    SHIELD = "🛡️"
    CHECK = "✓"
    CROSS = "✗"
    TOOL = "🔧"
    BRAIN = "🧠"
    CHART = "📊"
    FOLDER = "📁"
    SEARCH = "🔍"
    HOURGLASS = "⏳"
    PLAY = "▶"
    BULLET = "•"
    SPARK = "✨"
    LOCK = "🔒"
    KEY = "🔑"
    DIFF_ADD = "+"
    DIFF_DEL = "-"
    TERMINAL = "💻"
    ARROW_RIGHT = "→"
    DIAMOND = "◈"
    DOT = "●"
    PULSE = "◉"
    GEAR = "⚙"
    CORNER = "└─"
    PIPE = "│"
    CHEVRON = "›"
    DOUBLE_CHEVRON = "»"
    RETURN = "↵"
    LINK = "🔗"
    FILE = "📄"
    INFO = "ℹ"
    WARNING = "⚠"
    DATABASE = "🗄️"
    ROCKET = "🚀"

    @classmethod
    def get_prompt_symbol(cls, mode: str = "general") -> str:
        return f"{cls.LIGHTNING} JARVIS"

    @classmethod
    def get_mode_badge(cls, mode: str = "general") -> str:
        color = MODE_COLORS.get(mode.lower(), COLOR_CYAN)
        return f"[{color} bold]{mode.upper()}[/]"


def get_terminal_theme() -> Theme | None:
    """Generate custom Rich Theme for BR JARVIS CLI."""
    if not HAS_RICH:
        return None
    return Theme(
        {
            "jarvis.primary": f"bold {COLOR_CYAN}",
            "jarvis.secondary": COLOR_BLUE,
            "jarvis.success": f"bold {COLOR_GREEN}",
            "jarvis.warning": f"bold {COLOR_AMBER}",
            "jarvis.danger": f"bold {COLOR_RED}",
            "jarvis.accent": f"bold {COLOR_MAGENTA}",
            "jarvis.dim": COLOR_DIM,
            "jarvis.highlight": f"bold {COLOR_WHITE}",
            "jarvis.teal": f"bold {COLOR_TEAL}",
            "jarvis.orange": f"bold {COLOR_ORANGE}",
            "jarvis.muted": COLOR_MUTED,
            # Tool styles
            "tool.name": f"bold {COLOR_CYAN}",
            "tool.arg.key": f"{COLOR_TEAL}",
            "tool.arg.val": f"{COLOR_WHITE}",
            "tool.success": f"bold {COLOR_GREEN}",
            "tool.failed": f"bold {COLOR_RED}",
            "tool.latency": f"dim {COLOR_DIM}",
            # Verification styles
            "verify.pass": f"bold {COLOR_GREEN}",
            "verify.fail": f"bold {COLOR_RED}",
            "verify.evidence": f"{COLOR_DIM}",
            # Prompt styles
            "prompt.user": f"bold {COLOR_CYAN}",
            "prompt.mode": f"bold {COLOR_AMBER}",
            "prompt.arrow": f"bold {COLOR_TEAL}",
            # Markdown & Callout styles
            "callout.note": f"bold {COLOR_CYAN}",
            "callout.tip": f"bold {COLOR_GREEN}",
            "callout.warning": f"bold {COLOR_AMBER}",
            "callout.danger": f"bold {COLOR_RED}",
            "callout.important": f"bold {COLOR_MAGENTA}",
        }
    )
