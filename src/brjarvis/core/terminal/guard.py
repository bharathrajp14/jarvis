# core/terminal/guard.py — Terminal Lifecycle State Guard & Restoration for BR JARVIS MK41
"""
Terminal Lifecycle State Guard.
Manages alternate screen buffers, mouse tracking modes (Normal, Highlight, Any, SGR),
cursor visibility, and emergency signal-safe terminal restoration.
Guarantees the user's terminal is never left corrupted.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import os
import signal
import sys
from typing import Any, Generator, Optional

from .events import MouseCaptureMode

logger = logging.getLogger("JARVIS.TerminalGuard")

# ── ANSI Escape Sequences ─────────────────────────────────────────────────────

# Alternate screen buffer
ENTER_ALT_SCREEN = "\033[?1049h"
EXIT_ALT_SCREEN = "\033[?1049l"

# Cursor visibility
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Bracketed paste
ENABLE_BRACKETED_PASTE = "\033[?2004h"
DISABLE_BRACKETED_PASTE = "\033[?2004l"

# Mouse tracking modes
ENABLE_MOUSE_SGR = "\033[?1006h"  # SGR extended coordinates mode
DISABLE_MOUSE_SGR = "\033[?1006l"

ENABLE_MOUSE_BUTTON = "\033[?1000h"  # Report button click & release
DISABLE_MOUSE_BUTTON = "\033[?1000l"

ENABLE_MOUSE_DRAG = "\033[?1002h"  # Report button events & mouse drag
DISABLE_MOUSE_DRAG = "\033[?1002l"

ENABLE_MOUSE_ALL = "\033[?1003h"  # Report all mouse movements (hover)
DISABLE_MOUSE_ALL = "\033[?1003l"

# Reset all attributes & clear line
RESET_TERMINAL_ATTRIBUTES = "\033[0m"


class TerminalStateGuard:
    """
    Guards terminal state and restores it on normal exit, crash, Ctrl+C, or editor launch.
    """

    _instance: Optional[TerminalStateGuard] = None

    def __init__(self):
        self.is_alt_screen: bool = False
        self.is_cursor_hidden: bool = False
        self.mouse_mode: MouseCaptureMode = MouseCaptureMode.MOUSE_OFF
        self.is_mouse_active: bool = False
        self._registered_cleanup: bool = False
        self._prev_sigint: Optional[Any] = None
        self._prev_sigterm: Optional[Any] = None
        self._prev_sigwinch: Optional[Any] = None

        # Windows console mode tracking
        self._orig_conin_mode: Optional[int] = None
        self._orig_conout_mode: Optional[int] = None
        self._conin_handle: Optional[Any] = None
        self._conout_handle: Optional[Any] = None

    @classmethod
    def get_instance(cls) -> TerminalStateGuard:
        if cls._instance is None:
            cls._instance = TerminalStateGuard()
        return cls._instance

    def register_emergency_cleanup(self) -> None:
        """Register atexit and signal handlers to guarantee terminal restoration."""
        if self._registered_cleanup:
            return
        self._registered_cleanup = True

        atexit.register(self.restore_all)

        # Register signal handlers safely
        try:
            self._prev_sigint = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, self._on_signal)
        except Exception:
            pass

        try:
            self._prev_sigterm = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGTERM, self._on_signal)
        except Exception:
            pass

    def _on_signal(self, signum: int, frame: Any) -> None:
        """Emergency restoration on signal before propagating."""
        self.restore_all()
        if (
            signum == signal.SIGINT
            and callable(self._prev_sigint)
            and self._prev_sigint not in (signal.SIG_IGN, signal.SIG_DFL, self._on_signal)
        ):
            self._prev_sigint(signum, frame)
        elif (
            signum == signal.SIGTERM
            and callable(self._prev_sigterm)
            and self._prev_sigterm not in (signal.SIG_IGN, signal.SIG_DFL, self._on_signal)
        ):
            self._prev_sigterm(signum, frame)
        else:
            sys.exit(130 if signum == signal.SIGINT else 143)

    def _write_raw(self, seq: str) -> None:
        """Write raw ANSI sequences directly to stdout and flush."""
        try:
            if hasattr(sys.stdout, "write") and hasattr(sys.stdout, "flush"):
                sys.stdout.write(seq)
                sys.stdout.flush()
        except Exception:
            pass

    # ── Windows Console Win32 Mode Management ────────────────────────────────

    def _enable_windows_mouse_mode(self) -> None:
        """Enable mouse input and disable QuickEdit on Windows consoles via Win32 API."""
        if os.name != "nt":
            return
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            GENERIC_READ_WRITE = 0x80000000 | 0x40000000
            FILE_SHARE_READ_WRITE = 0x00000001 | 0x00000002
            OPEN_EXISTING = 3

            ENABLE_WINDOW_INPUT = 0x0008
            ENABLE_MOUSE_INPUT = 0x0010
            ENABLE_QUICK_EDIT_MODE = 0x0040
            ENABLE_EXTENDED_FLAGS = 0x0080
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

            # Open CONIN$ to access real console input buffer even if redirected
            h_in = kernel32.CreateFileW(
                "CONIN$", GENERIC_READ_WRITE, FILE_SHARE_READ_WRITE, None, OPEN_EXISTING, 0, None
            )
            if h_in and h_in != -1:
                self._conin_handle = h_in
                mode_in = ctypes.c_ulong()
                if kernel32.GetConsoleMode(h_in, ctypes.byref(mode_in)):
                    if self._orig_conin_mode is None:
                        self._orig_conin_mode = mode_in.value

                    # Disable QuickEdit & enable mouse input
                    new_mode_in = (
                        mode_in.value | ENABLE_MOUSE_INPUT | ENABLE_WINDOW_INPUT | ENABLE_EXTENDED_FLAGS
                    ) & ~ENABLE_QUICK_EDIT_MODE
                    kernel32.SetConsoleMode(h_in, new_mode_in)

            # Open CONOUT$ to enable Virtual Terminal Processing
            h_out = kernel32.CreateFileW(
                "CONOUT$", GENERIC_READ_WRITE, FILE_SHARE_READ_WRITE, None, OPEN_EXISTING, 0, None
            )
            if h_out and h_out != -1:
                self._conout_handle = h_out
                mode_out = ctypes.c_ulong()
                if kernel32.GetConsoleMode(h_out, ctypes.byref(mode_out)):
                    if self._orig_conout_mode is None:
                        self._orig_conout_mode = mode_out.value
                    new_mode_out = mode_out.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    kernel32.SetConsoleMode(h_out, new_mode_out)
        except Exception as e:
            logger.debug("Win32 console mouse mode setup note: %s", e)

    def _restore_windows_console_mode(self) -> None:
        """Restore original Windows console input & output modes."""
        if os.name != "nt":
            return
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            ENABLE_EXTENDED_FLAGS = 0x0080

            if self._conin_handle and self._orig_conin_mode is not None:
                kernel32.SetConsoleMode(self._conin_handle, self._orig_conin_mode | ENABLE_EXTENDED_FLAGS)

            if self._conout_handle and self._orig_conout_mode is not None:
                kernel32.SetConsoleMode(self._conout_handle, self._orig_conout_mode)
        except Exception as e:
            logger.debug("Win32 console restore note: %s", e)

    # ── State Transitions ─────────────────────────────────────────────────────

    def enter_alternate_screen(self) -> None:
        """Switch to alternate screen buffer."""
        if not self.is_alt_screen:
            self._write_raw(ENTER_ALT_SCREEN)
            self.is_alt_screen = True

    def exit_alternate_screen(self) -> None:
        """Restore primary screen buffer."""
        if self.is_alt_screen:
            self._write_raw(EXIT_ALT_SCREEN)
            self.is_alt_screen = False

    def hide_cursor(self) -> None:
        """Hide cursor during fullscreen rendering."""
        if not self.is_cursor_hidden:
            self._write_raw(HIDE_CURSOR)
            self.is_cursor_hidden = True

    def show_cursor(self) -> None:
        """Restore visible cursor."""
        if self.is_cursor_hidden:
            self._write_raw(SHOW_CURSOR)
            self.is_cursor_hidden = False

    def enable_mouse_capture(self, mode: MouseCaptureMode = MouseCaptureMode.MOUSE_INTERACTIVE) -> None:
        """
        Enable mouse reporting based on capture mode:
        - MOUSE_OFF: No sequences emitted.
        - MOUSE_SCROLL / MOUSE_INTERACTIVE: SGR + Drag mode (1002 + 1006).
        - MOUSE_FULL: SGR + All events mode (1003 + 1006).
        """
        self.mouse_mode = mode
        if mode == MouseCaptureMode.MOUSE_OFF:
            self.disable_mouse_capture()
            return

        # 1. Configure Win32 Console Modes on Windows
        self._enable_windows_mouse_mode()

        # 2. Emit ANSI / VT Escape Sequences for modern terminal emulators
        seqs = [ENABLE_MOUSE_SGR]
        if mode == MouseCaptureMode.MOUSE_FULL:
            seqs.append(ENABLE_MOUSE_ALL)
        else:  # MOUSE_SCROLL or MOUSE_INTERACTIVE
            seqs.append(ENABLE_MOUSE_DRAG)

        self._write_raw("".join(seqs))
        self.is_mouse_active = True

    def disable_mouse_capture(self) -> None:
        """Disable all terminal mouse tracking protocols."""
        self._restore_windows_console_mode()
        seqs = [
            DISABLE_MOUSE_ALL,
            DISABLE_MOUSE_DRAG,
            DISABLE_MOUSE_BUTTON,
            DISABLE_MOUSE_SGR,
        ]
        self._write_raw("".join(seqs))
        self.is_mouse_active = False

    def restore_all(self) -> None:
        """Perform comprehensive terminal state restoration."""
        self.disable_mouse_capture()
        self.show_cursor()
        self._write_raw(DISABLE_BRACKETED_PASTE)
        self._write_raw(RESET_TERMINAL_ATTRIBUTES)
        self.exit_alternate_screen()

    @contextlib.contextmanager
    def suspend_for_external(self) -> Generator[None, None, None]:
        """
        Temporarily restore normal terminal mode while launching an external process
        (such as $EDITOR, git, or interactive shell), then re-enable TUI state upon return.
        """
        prev_alt = self.is_alt_screen
        prev_mouse = self.is_mouse_active
        prev_mouse_mode = self.mouse_mode

        try:
            self.restore_all()
            yield
        finally:
            if prev_alt:
                self.enter_alternate_screen()
            if prev_mouse:
                self.enable_mouse_capture(prev_mouse_mode)
