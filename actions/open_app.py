# actions/open_app.py
"""
BR Voice Assistant — Application Launcher.
Cross-platform implementation for Linux, macOS, and Windows.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time

_OS = platform.system()

_APP_ALIASES: dict[str, str] = {
    "chrome":             "google-chrome" if _OS == "Linux" else "chrome",
    "google chrome":      "google-chrome" if _OS == "Linux" else "chrome",
    "firefox":            "firefox",
    "edge":               "microsoft-edge" if _OS == "Linux" else "msedge",
    "brave":              "brave-browser" if _OS == "Linux" else "brave",
    "safari":             "safari" if _OS == "Darwin" else "firefox",
    "whatsapp":           "whatsapp",
    "telegram":           "telegram-desktop" if _OS == "Linux" else "Telegram",
    "discord":            "discord",
    "slack":              "slack",
    "zoom":               "zoom",
    "teams":              "teams",
    "spotify":            "spotify",
    "vlc":                "vlc",
    "vscode":             "code",
    "visual studio code": "code",
    "code":               "code",
    "terminal":           "x-terminal-emulator" if _OS == "Linux" else ("Terminal" if _OS == "Darwin" else "wt"),
    "cmd":                "bash" if _OS != "Windows" else "cmd.exe",
    "powershell":         "pwsh" if _OS != "Windows" else "powershell.exe",
    "notepad":            "gedit" if _OS == "Linux" else ("TextEdit" if _OS == "Darwin" else "notepad.exe"),
    "textedit":           "gedit" if _OS == "Linux" else ("TextEdit" if _OS == "Darwin" else "notepad.exe"),
    "explorer":           "nautilus" if _OS == "Linux" else ("Finder" if _OS == "Darwin" else "explorer.exe"),
    "file explorer":      "nautilus" if _OS == "Linux" else ("Finder" if _OS == "Darwin" else "explorer.exe"),
    "finder":             "nautilus" if _OS == "Linux" else ("Finder" if _OS == "Darwin" else "explorer.exe"),
    "task manager":       "gnome-system-monitor" if _OS == "Linux" else ("Activity Monitor" if _OS == "Darwin" else "taskmgr.exe"),
    "settings":           "gnome-control-center" if _OS == "Linux" else ("ms-settings:" if _OS == "Windows" else "System Settings"),
    "calculator":         "gnome-calculator" if _OS == "Linux" else ("Calculator" if _OS == "Darwin" else "calc.exe"),
    "paint":              "gimp" if _OS == "Linux" else ("mspaint.exe" if _OS == "Windows" else "Paint"),
}


def _normalize(raw: str) -> str:
    key = raw.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key]

    for alias_key, val in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return val
    return raw


def _launch_linux(app_name: str) -> bool:
    # 1. Direct executable in PATH check
    candidates = [
        app_name,
        app_name.lower(),
        app_name.split(".")[0],
    ]
    
    # Fallback alternatives for standard linux desktop components
    if app_name in ("gedit", "notepad"):
        candidates.extend(["kate", "mousepad", "xed", "pluma", "leafpad", "nano"])
    elif app_name in ("nautilus", "explorer"):
        candidates.extend(["dolphin", "thunar", "nemo", "pcmanfm"])
    elif app_name in ("gnome-system-monitor", "taskmgr"):
        candidates.extend(["htop", "ksysguard", "top"])
    elif app_name in ("x-terminal-emulator", "wt"):
        candidates.extend(["gnome-terminal", "alacritty", "konsole", "kitty", "xfce4-terminal", "xterm"])
    elif app_name in ("gnome-calculator", "calc"):
        candidates.extend(["kcalc", "galculator", "xcalc"])

    for cand in candidates:
        bin_path = shutil.which(cand)
        if bin_path:
            try:
                subprocess.Popen(
                    [bin_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                time.sleep(1.0)
                return True
            except Exception as e:
                print(f"[open_app] Launch failed for '{cand}': {e}")

    # 2. Try gtk-launch
    if shutil.which("gtk-launch"):
        try:
            res = subprocess.run(["gtk-launch", app_name], capture_output=True)
            if res.returncode == 0:
                return True
        except Exception:
            pass

    # 3. Try xdg-open if path or URI
    if shutil.which("xdg-open"):
        try:
            subprocess.Popen(
                ["xdg-open", app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return True
        except Exception:
            pass

    return False


def _launch_mac(app_name: str) -> bool:
    try:
        subprocess.Popen(["open", "-a", app_name])
        return True
    except Exception as e:
        print(f"[open_app] macOS launch failed: {e}")
        return False


def _launch_windows(app_name: str) -> bool:
    clean = app_name.strip()

    # 1. Primary Windows ShellExecute via os.startfile (resolves App Paths registry, UWP apps & protocols)
    try:
        os.startfile(clean)
        time.sleep(1.0)
        return True
    except Exception:
        pass

    # 2. Try with .exe extension fallback
    if not clean.endswith(".exe"):
        try:
            os.startfile(f"{clean}.exe")
            time.sleep(1.0)
            return True
        except Exception:
            pass

    # 3. Direct executable PATH check
    exe_path = shutil.which(clean) or shutil.which(clean.split(".")[0])
    if exe_path:
        try:
            subprocess.Popen(
                [exe_path],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] subprocess failed: {e}")

    # 4. Windows Start Menu GUI search fallback
    try:
        import pyautogui
        pyautogui.PAUSE = 0.1
        pyautogui.press("win")
        time.sleep(0.5)
        pyautogui.write(clean, interval=0.03)
        time.sleep(0.6)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] Start Menu search failed: {e}")

    return False


def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "No application name provided."

    target_url = (parameters or {}).get("url", "").strip()
    if not target_url:
        low_app = app_name.lower()
        if "youtube" in low_app:
            target_url = "https://www.youtube.com"
        elif "github" in low_app:
            target_url = "https://github.com"
        elif " google.com" in low_app or "google search" in low_app:
            target_url = "https://www.google.com"

    normalized = _normalize(app_name)
    print(f"[open_app] Launching: '{app_name}' → '{normalized}' (URL: '{target_url}') ({_OS})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        success = False
        if target_url:
            import webbrowser
            if _OS == "Windows":
                try:
                    os.startfile(target_url)
                    success = True
                    msg = f"Opened {target_url} in default browser."
                except Exception:
                    webbrowser.open(target_url)
                    success = True
                    msg = f"Opened {target_url} in browser."
            else:
                webbrowser.open(target_url)
                success = True
                msg = f"Opened {target_url} in default browser."
        elif _OS == "Linux":
            if _launch_linux(normalized) or _launch_linux(app_name):
                success = True
                msg = f"Opened {app_name}."
        elif _OS == "Darwin":
            if _launch_mac(normalized) or _launch_mac(app_name):
                success = True
                msg = f"Opened {app_name}."
        else:
            if _launch_windows(normalized) or _launch_windows(app_name):
                success = True
                msg = f"Opened {app_name}."

        if success:
            try:
                from actions.app_tracker import log_app_launch
                log_app_launch(app_name=app_name, source="jarvis_automated", details={"url": target_url})
            except Exception:
                pass
            return msg

        return f"Could not launch application: '{app_name}' on {_OS}."
    except Exception as e:
        return f"Error launching app '{app_name}': {e}"
