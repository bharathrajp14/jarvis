# tools/window_manager.py — Smart Desktop Window & Process Manager Tool for JARVIS
"""
Native Win32 window & process management tool.
Allows JARVIS to list open windows, bring applications to focus, inspect processes,
and manage desktop layout autonomously.
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
            if title:
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
            win32gui.SetForegroundWindow(target_hwnd)
            return f"Successfully focused window: '{target_title}'"
        else:
            return f"No open window found matching '{title_query}'"
    except Exception as e:
        return f"Error focusing window: {e}"


def window_manager_action(args: Dict[str, Any]) -> str:
    """
    Main tool handler for desktop window and process control.
    Actions: 'list', 'focus'.
    """
    action = str(args.get("action", "list")).lower().strip()
    title = str(args.get("title", "")).strip()

    if action in ("list", "show", "get"):
        wins = list_desktop_windows()
        if not wins:
            return "No visible desktop windows found."
        lines = [f"Desktop Windows ({len(wins)} active):"]
        for w in wins[:20]:
            lines.append(f"• [PID {w.get('pid', '?')}] {w.get('title')}")
        return "\n".join(lines)

    elif action in ("focus", "activate", "switch"):
        if not title:
            return "Error: 'title' argument required for focus action."
        return focus_window_by_title(title)

    else:
        return f"Unknown window_manager action '{action}'. Valid actions: list, focus."
