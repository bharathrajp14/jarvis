# core/terminal/selection.py — Text Selection & Cross-Platform Clipboard for BR JARVIS MK41
"""
Text Selection and Cross-Platform Clipboard Subsystem.
Handles character, word (with path/URL boundary awareness), line, and block selection,
along with safe clipboard access across Windows (Win32), Linux (wl-copy/xclip), macOS (pbcopy),
and OSC 52 fallback for remote SSH/tmux sessions.
"""

from __future__ import annotations

import base64
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

logger = logging.getLogger("JARVIS.Selection")


class SelectionMode(str, Enum):
    NONE = "none"
    CHAR = "char"
    WORD = "word"
    LINE = "line"
    BLOCK = "block"


@dataclass
class SelectionRange:
    """Text selection coordinates (0-indexed line and col)."""

    start_row: int = 0
    start_col: int = 0
    end_row: int = 0
    end_col: int = 0
    mode: SelectionMode = SelectionMode.NONE

    @property
    def is_active(self) -> bool:
        return self.mode != SelectionMode.NONE and (self.start_row != self.end_row or self.start_col != self.end_col)

    def normalized(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Return ((top_row, left_col), (bottom_row, right_col)) regardless of drag direction."""
        if (self.start_row, self.start_col) <= (self.end_row, self.end_col):
            return (self.start_row, self.start_col), (self.end_row, self.end_col)
        return (self.end_row, self.end_col), (self.start_row, self.start_col)


# ── Cross-Platform Clipboard Provider ────────────────────────────────────────


class ClipboardProvider:
    """
    Robust cross-platform clipboard provider supporting Windows Win32 API,
    Linux wl-copy / xclip / xsel, macOS pbcopy, and OSC 52 escape sequences for SSH/tmux.
    Never crashes the terminal on clipboard failure.
    """

    @classmethod
    def copy(cls, text: str) -> bool:
        """Copy text to system or terminal clipboard."""
        if not text:
            return False

        system = platform.system().lower()

        # 1. Windows (ctypes Win32 API or clip.exe)
        if system == "windows" or os.name == "nt":
            if cls._copy_windows_ctypes(text):
                return True
            if cls._copy_subprocess(["clip"], text):
                return True

        # 2. macOS (pbcopy)
        elif system == "darwin":
            if cls._copy_subprocess(["pbcopy"], text):
                return True

        # 3. Linux (wl-copy -> xclip -> xsel)
        else:
            if shutil.which("wl-copy") and cls._copy_subprocess(["wl-copy"], text):
                return True
            if shutil.which("xclip") and cls._copy_subprocess(["xclip", "-selection", "clipboard"], text):
                return True
            if shutil.which("xsel") and cls._copy_subprocess(["xsel", "--clipboard", "--input"], text):
                return True

        # 4. Fallback: OSC 52 ANSI escape sequence (works over SSH and in modern terminals)
        return cls._copy_osc52(text)

    @classmethod
    def _copy_windows_ctypes(cls, text: str) -> bool:
        """Direct Win32 Clipboard via ctypes."""
        try:
            import ctypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            GMEM_MOVEABLE = 0x0002
            CF_UNICODETEXT = 13

            if not user32.OpenClipboard(None):
                return False
            try:
                user32.EmptyClipboard()
                utf16 = text.encode("utf-16le") + b"\x00\x00"
                h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(utf16))
                if not h_mem:
                    return False
                p_mem = kernel32.GlobalLock(h_mem)
                if not p_mem:
                    return False
                ctypes.memmove(p_mem, utf16, len(utf16))
                kernel32.GlobalUnlock(h_mem)
                return bool(user32.SetClipboardData(CF_UNICODETEXT, h_mem))
            finally:
                user32.CloseClipboard()
        except Exception:
            return False

    @classmethod
    def _copy_subprocess(cls, cmd: list[str], text: str) -> bool:
        """Pipe text to clipboard command."""
        try:
            p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            p.communicate(input=text, timeout=2.0)
            return p.returncode == 0
        except Exception:
            return False

    @classmethod
    def _copy_osc52(cls, text: str) -> bool:
        """Emit OSC 52 clipboard write sequence."""
        try:
            b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
            # In tmux, wrap with DSC
            if os.environ.get("TMUX"):
                seq = f"\033Ptmux;\033\033]52;c;{b64}\a\033\\"
            else:
                seq = f"\033]52;c;{b64}\a"
            sys.stdout.write(seq)
            sys.stdout.flush()
            return True
        except Exception:
            return False


# ── Selection Manager ────────────────────────────────────────────────────────


class SelectionManager:
    """
    Manages interactive text selections, word boundary detection (including path/URL awareness),
    and line selections.
    """

    # Characters that form word tokens in programming/paths
    _PATH_CHARS = re.compile(r"[\w\-\./\\:~]")

    def __init__(self, copy_on_select: bool = False):
        self.selection: SelectionRange = SelectionRange()
        self.copy_on_select: bool = copy_on_select

    def start_selection(self, row: int, col: int, mode: SelectionMode = SelectionMode.CHAR) -> None:
        """Start a new selection drag."""
        self.selection = SelectionRange(
            start_row=row,
            start_col=col,
            end_row=row,
            end_col=col,
            mode=mode,
        )

    def update_selection(self, row: int, col: int) -> None:
        """Update active selection endpoint."""
        if self.selection.mode != SelectionMode.NONE:
            self.selection.end_row = row
            self.selection.end_col = col

    def end_selection(self, lines: Optional[list[str]] = None) -> Optional[str]:
        """Finish selection and optionally copy text to clipboard."""
        if not self.selection.is_active:
            self.clear()
            return None

        extracted = None
        if lines:
            extracted = self.extract_selected_text(lines)
            if extracted and self.copy_on_select:
                ClipboardProvider.copy(extracted)

        return extracted

    def clear(self) -> None:
        """Reset selection."""
        self.selection = SelectionRange()

    def select_word_at(self, line: str, row: int, col: int) -> Tuple[int, int]:
        """
        Detect word boundary at col index in line.
        Preserves complete file paths (e.g. src/brjarvis/core/guard.py:12) and URLs as a single unit.
        """
        if not line or col < 0 or col >= len(line):
            self.selection = SelectionRange(
                start_row=row, start_col=col, end_row=row, end_col=col, mode=SelectionMode.WORD
            )
            return col, col

        # Search left
        start = col
        while start > 0 and self._PATH_CHARS.match(line[start - 1]):
            start -= 1

        # Search right
        end = col
        while end < len(line) and self._PATH_CHARS.match(line[end]):
            end += 1

        self.selection = SelectionRange(
            start_row=row,
            start_col=start,
            end_row=row,
            end_col=end,
            mode=SelectionMode.WORD,
        )
        return start, end

    def select_line_at(self, line: str, row: int) -> Tuple[int, int]:
        """Select entire line on triple-click."""
        self.selection = SelectionRange(
            start_row=row,
            start_col=0,
            end_row=row,
            end_col=len(line),
            mode=SelectionMode.LINE,
        )
        return 0, len(line)

    def extract_selected_text(self, lines: list[str]) -> str:
        """Extract plain text string spanning the normalized selection range."""
        if not self.selection.is_active or not lines:
            return ""

        (r1, c1), (r2, c2) = self.selection.normalized()
        r1 = max(0, min(r1, len(lines) - 1))
        r2 = max(0, min(r2, len(lines) - 1))

        if r1 == r2:
            line = lines[r1]
            return line[max(0, c1) : min(len(line), c2)]

        selected_parts = []
        for r in range(r1, r2 + 1):
            line = lines[r] if r < len(lines) else ""
            if r == r1:
                selected_parts.append(line[max(0, c1) :])
            elif r == r2:
                selected_parts.append(line[: min(len(line), c2)])
            else:
                selected_parts.append(line)

        return "\n".join(selected_parts)
