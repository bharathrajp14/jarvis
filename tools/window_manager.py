# tools/window_manager.py — Smart Desktop Window & Process Manager Tool for JARVIS
"""
Native Win32 window & process management tool.
Allows JARVIS to list open windows, bring applications to focus, inspect processes,
minimize/maximize windows, and manage desktop layout autonomously.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Any

_HAS_WIN32 = False
if sys.platform == "win32":
    try:
        import win32gui
        import win32process
        import win32con
        _HAS_WIN32 = True
    except ImportError:
        _HAS_WIN32 = False


def list_desktop_windows() -> List[Dict[str, Any]]:
    """List all visible desktop application windows with title and PID."""
    windows = []
    if not _HAS_WIN32:
        return [{"title": "Win32 API not available (Non-Windows or missing pywin32)", "pid": 0}]

    def enum_handler(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title and title not in ("Program Manager", "Settings", "Default IME", "MSCTFIME UI"):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                windows.append({
                    "hwnd": hwnd,
                    "title": title,
                    "pid": pid,
                })

    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception as e:
        windows.append({"error": str(e)})

    return windows


def focus_window_by_title(title_query: str) -> str:
    """Bring window matching title_query to focus and foreground."""
    if not _HAS_WIN32:
        return "Win32 API not available for window focus."

    query_low = title_query.lower().strip()
    target_hwnd = None
    target_title = ""

    def enum_handler(hwnd, extra):
        nonlocal target_hwnd, target_title
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            if query_low in t.lower():
                target_hwnd = hwnd
                target_title = t

    try:
        win32gui.EnumWindows(enum_handler, None)
        if target_hwnd:
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            try:
                win32gui.SetForegroundWindow(target_hwnd)
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
            return f"Focused window: '{target_title}' (HWND: {target_hwnd})"
        return f"No visible window matching '{title_query}' was found."
    except Exception as e:
        return f"Error focusing window: {e}"


def control_window_state(title_query: str, state: str = "minimize") -> str:
    """Minimize, maximize, restore, or close a window matching title_query."""
    if not _HAS_WIN32:
        return "Win32 API not available for window state management."

    query_low = title_query.lower().strip()
    st = state.lower().strip()
    target_hwnd = None
    target_title = ""

    def enum_handler(hwnd, extra):
        nonlocal target_hwnd, target_title
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            if query_low in t.lower():
                target_hwnd = hwnd
                target_title = t

    try:
        win32gui.EnumWindows(enum_handler, None)
        if not target_hwnd:
            return f"No window matching '{title_query}' found."

        if st == "minimize":
            win32gui.ShowWindow(target_hwnd, win32con.SW_MINIMIZE)
            return f"Minimized window: '{target_title}'"
        elif st == "maximize":
            win32gui.ShowWindow(target_hwnd, win32con.SW_MAXIMIZE)
            return f"Maximized window: '{target_title}'"
        elif st == "restore":
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            return f"Restored window: '{target_title}'"
        elif st == "close":
            win32gui.PostMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
            return f"Closed window: '{target_title}'"
        else:
            return f"Unknown state action '{state}'. Use: minimize, maximize, restore, close."
    except Exception as e:
        return f"Error managing window state: {e}"


def window_manager_action(action: Any = "list", title: str = "", state: str = "focus") -> str:
    """Tool function for inspecting and focusing windows."""
    if isinstance(action, dict):
        args = action
        action = args.get("action", "list")
        title = args.get("title", "")
        state = args.get("state", "focus")

    act = str(action or "list").lower().strip()
    if act in ("list", "show", "enum"):
        wins = list_desktop_windows()
        if not wins:
            return "No visible Desktop Windows found."
        lines = [f"- PID {w['pid']}: {w['title']}" for w in wins if "title" in w]
        return f"🖥️ Active Desktop Windows ({len(lines)}):\n" + "\n".join(lines)
    elif act in ("focus", "switch", "activate"):
        if not title:
            return "ERROR: 'title' parameter required for focus action."
        return focus_window_by_title(title)
    elif act in ("minimize", "maximize", "restore", "close"):
        if not title:
            return "ERROR: 'title' parameter required for window state management."
        return control_window_state(title, state=act)
    else:
        return f"ERROR: Unknown action '{action}'"
