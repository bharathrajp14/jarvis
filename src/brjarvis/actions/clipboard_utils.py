# actions/clipboard_utils.py — Unified Multi-Backend Clipboard Manager
"""
Robust, multi-backend system clipboard interface for BR JARVIS.
Provides fallbacks across pyperclip, Win32 API, Tkinter, PowerShell, and OS CLI commands.
"""

from __future__ import annotations

import logging
import platform
import subprocess
import threading

logger = logging.getLogger("JARVIS.ClipboardUtils")
_OS = platform.system()
_CLIPBOARD_LOCK = threading.Lock()


def get_clipboard_text() -> str:
    """
    Retrieve current plain text from the system clipboard.
    Uses multi-backend fallback strategy:
      1. pyperclip
      2. Win32 API (Windows)
      3. Tkinter (Cross-platform GUI)
      4. PowerShell Get-Clipboard (Windows CLI)
      5. pbpaste (macOS CLI)
      6. xclip / xsel / wl-paste (Linux CLI)
    Returns empty string if clipboard is empty or non-text.
    """
    with _CLIPBOARD_LOCK:
        # Backend 1: pyperclip
        try:
            import pyperclip

            val = pyperclip.paste()
            if isinstance(val, str) and val:
                return val
        except Exception as e:
            logger.debug(f"pyperclip.paste failed: {e}")

    # Backend 2: Win32 API (Windows native)
    if _OS == "Windows":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            CF_UNICODETEXT = 13
            if user32.OpenClipboard(None):
                try:
                    h_data = user32.GetClipboardData(CF_UNICODETEXT)
                    if h_data:
                        p_data = kernel32.GlobalLock(h_data)
                        if p_data:
                            try:
                                text = ctypes.wstring_at(p_data)
                                return text
                            finally:
                                kernel32.GlobalUnlock(h_data)
                finally:
                    user32.CloseClipboard()
        except Exception as e:
            logger.debug(f"Win32 clipboard access failed: {e}")

    # Backend 3: Tkinter
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            val = root.clipboard_get()
            if isinstance(val, str) and val:
                return val
        finally:
            root.destroy()
    except Exception as e:
        logger.debug(f"Tkinter clipboard_get failed: {e}")

    # Backend 4: Windows PowerShell
    if _OS == "Windows":
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=3,
                encoding="utf-8",
                errors="replace",
            )
            if res.returncode == 0:
                out = res.stdout
                # Strip trailing newline added by PowerShell if string is present
                if out.endswith("\r\n"):
                    out = out[:-2]
                elif out.endswith("\n"):
                    out = out[:-1]
                if out:
                    return out
        except Exception as e:
            logger.debug(f"PowerShell Get-Clipboard failed: {e}")

    # Backend 5: macOS pbpaste
    if _OS == "Darwin":
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3, encoding="utf-8")
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception as e:
            logger.debug(f"pbpaste failed: {e}")

    # Backend 6: Linux CLI tools
    if _OS == "Linux":
        for cmd in [
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "-clipboard", "-o"],
            ["wl-paste"],
        ]:
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, encoding="utf-8")
                if res.returncode == 0 and res.stdout:
                    return res.stdout
            except Exception:
                continue

    return ""


def set_clipboard_text(text: str) -> bool:
    """
    Write text to the system clipboard.
    Returns True if successfully set by any backend.
    """
    if text is None:
        text = ""

    # Backend 1: pyperclip
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception as e:
        logger.debug(f"pyperclip.copy failed: {e}")

    # Backend 2: Win32 API (Windows)
    if _OS == "Windows":
        try:
            import ctypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002

            text_bytes = (text + "\0").encode("utf-16le")
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
            if h_mem:
                p_mem = kernel32.GlobalLock(h_mem)
                if p_mem:
                    ctypes.memmove(p_mem, text_bytes, len(text_bytes))
                    kernel32.GlobalUnlock(h_mem)
                    if user32.OpenClipboard(None):
                        try:
                            user32.EmptyClipboard()
                            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                            return True
                        finally:
                            user32.CloseClipboard()
        except Exception as e:
            logger.debug(f"Win32 set clipboard failed: {e}")

    # Backend 3: Tkinter
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            return True
        finally:
            root.destroy()
    except Exception as e:
        logger.debug(f"Tkinter clipboard_append failed: {e}")

    # Backend 4: Windows PowerShell
    if _OS == "Windows":
        try:
            # Escape quotes in PowerShell string
            escaped = text.replace("`", "``").replace('"', '`"')
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f'Set-Clipboard -Value "{escaped}"'],
                capture_output=True,
                timeout=3,
            )
            if res.returncode == 0:
                return True
        except Exception as e:
            logger.debug(f"PowerShell Set-Clipboard failed: {e}")

    # Backend 5: macOS pbcopy
    if _OS == "Darwin":
        try:
            res = subprocess.run(["pbcopy"], input=text, text=True, timeout=3)
            if res.returncode == 0:
                return True
        except Exception as e:
            logger.debug(f"pbcopy failed: {e}")

    # Backend 6: Linux CLI tools
    if _OS == "Linux":
        for cmd in [
            ["xclip", "-selection", "clipboard"],
            ["xsel", "-clipboard", "-i"],
            ["wl-copy"],
        ]:
            try:
                res = subprocess.run(cmd, input=text, text=True, timeout=3)
                if res.returncode == 0:
                    return True
            except Exception:
                continue

    return False
