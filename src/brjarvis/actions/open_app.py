import logging
import platform
import shutil
import subprocess
import time

logger = logging.getLogger("JARVIS.Actions.OpenApp")

try:
    import psutil

    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_SYSTEM = platform.system()

_APP_ALIASES: dict[str, dict[str, str]] = {
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "google chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "firefox": {"Windows": "firefox", "Darwin": "Firefox", "Linux": "firefox"},
    "edge": {"Windows": "msedge", "Darwin": "Microsoft Edge", "Linux": "microsoft-edge"},
    "brave": {"Windows": "brave", "Darwin": "Brave Browser", "Linux": "brave-browser"},
    "safari": {"Windows": "msedge", "Darwin": "Safari", "Linux": "firefox"},
    "opera": {"Windows": "opera", "Darwin": "Opera", "Linux": "opera"},
    "whatsapp": {"Windows": "WhatsApp", "Darwin": "WhatsApp", "Linux": "whatsapp"},
    "telegram": {"Windows": "Telegram", "Darwin": "Telegram", "Linux": "telegram"},
    "discord": {"Windows": "Discord", "Darwin": "Discord", "Linux": "discord"},
    "slack": {"Windows": "Slack", "Darwin": "Slack", "Linux": "slack"},
    "zoom": {"Windows": "Zoom", "Darwin": "zoom.us", "Linux": "zoom"},
    "teams": {"Windows": "msteams", "Darwin": "Microsoft Teams", "Linux": "teams"},
    "skype": {"Windows": "skype", "Darwin": "Skype", "Linux": "skype"},
    "signal": {"Windows": "signal", "Darwin": "Signal", "Linux": "signal"},
    "spotify": {"Windows": "Spotify", "Darwin": "Spotify", "Linux": "spotify"},
    "vlc": {"Windows": "vlc", "Darwin": "VLC", "Linux": "vlc"},
    "netflix": {"Windows": "Netflix", "Darwin": "Netflix", "Linux": "firefox"},
    "vscode": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "visual studio code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "terminal": {"Windows": "wt", "Darwin": "Terminal", "Linux": "x-terminal-emulator"},
    "cmd": {"Windows": "cmd.exe", "Darwin": "Terminal", "Linux": "bash"},
    "powershell": {"Windows": "powershell.exe", "Darwin": "Terminal", "Linux": "bash"},
    "postman": {"Windows": "Postman", "Darwin": "Postman", "Linux": "postman"},
    "git": {"Windows": "git-bash", "Darwin": "Terminal", "Linux": "bash"},
    "figma": {"Windows": "Figma", "Darwin": "Figma", "Linux": "figma"},
    "blender": {"Windows": "blender", "Darwin": "Blender", "Linux": "blender"},
    "word": {"Windows": "winword", "Darwin": "Microsoft Word", "Linux": "libreoffice --writer"},
    "excel": {"Windows": "excel", "Darwin": "Microsoft Excel", "Linux": "libreoffice --calc"},
    "powerpoint": {"Windows": "powerpnt", "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "libreoffice": {"Windows": "soffice", "Darwin": "LibreOffice", "Linux": "libreoffice"},
    "notepad": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
    "textedit": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
    "explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "file explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "finder": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "task manager": {"Windows": "taskmgr.exe", "Darwin": "Activity Monitor", "Linux": "gnome-system-monitor"},
    "settings": {"Windows": "ms-settings:", "Darwin": "System Preferences", "Linux": "gnome-control-center"},
    "calculator": {"Windows": "calc.exe", "Darwin": "Calculator", "Linux": "gnome-calculator"},
    "paint": {"Windows": "mspaint.exe", "Darwin": "Preview", "Linux": "gimp"},
    "instagram": {"Windows": "Instagram", "Darwin": "Instagram", "Linux": "firefox"},
    "tiktok": {"Windows": "TikTok", "Darwin": "TikTok", "Linux": "firefox"},
    "notion": {"Windows": "Notion", "Darwin": "Notion", "Linux": "notion"},
    "obsidian": {"Windows": "Obsidian", "Darwin": "Obsidian", "Linux": "obsidian"},
    "capcut": {"Windows": "CapCut", "Darwin": "CapCut", "Linux": "capcut"},
    "steam": {"Windows": "steam", "Darwin": "Steam", "Linux": "steam"},
    "epic": {"Windows": "EpicGamesLauncher", "Darwin": "Epic Games Launcher", "Linux": "legendary"},
    "epic games": {"Windows": "EpicGamesLauncher", "Darwin": "Epic Games Launcher", "Linux": "legendary"},
}


def _normalize(raw: str) -> str:
    key = raw.lower().strip()

    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(_SYSTEM, raw)

    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(_SYSTEM, raw)

    return raw


def _launch_windows(app_name: str) -> bool:
    import os
    from pathlib import Path

    # 1. If target is a file on disk, launch via native os.startfile or ShellExecute
    clean_target = app_name.strip("\"'")
    p = Path(clean_target)
    if not p.is_absolute():
        p = Path.cwd() / p
    if p.exists():
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(p.resolve()))
                time.sleep(1.5)
                return True
        except Exception as e:
            logger.debug("[open_app] os.startfile failed: %s", e)

        try:
            import ctypes

            ret = ctypes.windll.shell32.ShellExecuteW(None, "open", str(p.resolve()), None, None, 1)
            if ret > 32:
                time.sleep(1.5)
                return True
        except Exception as e:
            logger.debug("[open_app] ShellExecuteW failed: %s", e)

    # 2. Executable in PATH
    if shutil.which(app_name) or shutil.which(app_name.split(".")[0]):
        try:
            subprocess.Popen(
                [app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.5)
            return True
        except Exception as e:
            logger.warning(f"[open_app] subprocess failed: {e}")

    # 3. Native start command
    try:
        if hasattr(os, "startfile"):
            try:
                os.startfile(app_name)
                time.sleep(1.5)
                return True
            except Exception:
                pass
        subprocess.Popen(["cmd.exe", "/c", "start", "", app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        return True
    except Exception:
        pass

    # 4. Start menu fallback
    try:
        import pyautogui

        pyautogui.PAUSE = 0.1
        pyautogui.press("win")
        time.sleep(0.7)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.9)
        pyautogui.press("enter")
        time.sleep(2.5)
        return True
    except Exception as e:
        logger.warning(f"[open_app] Start Menu search failed: {e}")

    return False


def _launch_macos(app_name: str) -> bool:

    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception as exc:
        logger.debug("[open_app] Mac app launch failed: %s", exc)

    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception as exc:
            logger.debug("[open_app] Binary launch failed: %s", exc)

    try:
        import pyautogui

        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        logger.warning("[open_app] Spotlight failed: %s", e)

    return False


_LINUX_TERMINAL_FALLBACKS = [
    "x-terminal-emulator",
    "gnome-terminal",
    "konsole",
    "xfce4-terminal",
    "xterm",
    "lxterminal",
    "mate-terminal",
    "tilix",
    "alacritty",
    "kitty",
]


def _launch_linux(app_name: str) -> bool:

    # terminal emulators: try common ones in order
    if app_name in ("x-terminal-emulator", "gnome-terminal", "terminal"):
        for term in _LINUX_TERMINAL_FALLBACKS:
            if shutil.which(term):
                try:
                    subprocess.Popen([term], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    return True
                except Exception:
                    continue

    binary = (
        shutil.which(app_name)
        or shutil.which(app_name.lower())
        or shutil.which(app_name.lower().replace(" ", "-"))
        or shutil.which(app_name.lower().replace(" ", "_"))
    )
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        subprocess.run(["xdg-open", app_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass

    for desktop_name in [
        app_name.lower(),
        app_name.lower().replace(" ", "-"),
        app_name.lower().replace(" ", ""),
    ]:
        try:
            result = subprocess.run(["gtk-launch", desktop_name], capture_output=True, timeout=5)
            if result.returncode == 0:
                return True
        except Exception:
            pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin": _launch_macos,
    "Linux": _launch_linux,
}


def open_app(
    parameters: dict,
    player=None,
    active_character=None,
    session_memory=None,
) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()
    url = (parameters or {}).get("url", "").strip()

    if not app_name and url:
        app_name = "chrome"

    if not app_name:
        return "No application name provided."

    # Sandbox Artifact Interception Gateway
    low = app_name.lower().replace("\\", "/")
    if "jarvis_sandbox_jails" in low or "/jail_" in low or "\\jail_" in app_name.lower():
        try:
            from brjarvis.agent.artifacts import get_artifact_manager

            mgr = get_artifact_manager()
            parts = app_name.split(maxsplit=1)
            if len(parts) == 2 and any(
                b in parts[0].lower() for b in ("chrome", "msedge", "edge", "brave", "firefox", "start", "open")
            ):
                prefix, target_path = parts[0], parts[1].strip("\"'")
                success, resolved_target, _ = mgr.ensure_host_artifact(target_path)
                if not success:
                    return f"Artifact created, but could not export it to the user workspace: {resolved_target}"
                app_name = f"{prefix} {resolved_target}"
            else:
                target_clean = app_name.strip("\"'")
                success, resolved_target, _ = mgr.ensure_host_artifact(target_clean)
                if not success:
                    return f"Artifact created, but could not export it to the user workspace: {resolved_target}"
                app_name = resolved_target
        except Exception as e:
            logger.debug("Artifact interception note: %s", e)

    # 1. Primary Strategy: Auto-Configuring ApplicationResolver Engine
    try:
        from brjarvis.actions.app_resolver import get_app_resolver

        resolver = get_app_resolver()
        success, msg = resolver.launch(app_name, url=url)
        if success:
            if player:
                player.write_log(f"[open_app] {app_name} -> {msg}")
            return f"✅ {msg}"
    except Exception as e:
        logger.debug("[open_app] AppResolver note: %s", e)

    # 2. Secondary Strategy: OS Native Launchers Fallback
    launcher = _OS_LAUNCHERS.get(_SYSTEM)
    if launcher is None:
        return f"Unsupported operating system: {_SYSTEM}"

    normalized = _normalize(app_name)
    logger.info(f"[open_app] Launching via fallback: '{app_name}' → '{normalized}' ({_SYSTEM})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        launched = launcher(normalized)
        if not launched and normalized.lower() != app_name.lower():
            launched = launcher(app_name)

        if not launched:
            return (
                f"[FAILED] Could not find or launch application '{app_name}'. "
                f"Please verify the app name or run 'sync_app_paths' to re-scan installed software."
            )

        # Verify process and window actually started
        try:
            from brjarvis.core.execution.verifier import ApplicationVerifier

            proc_name = normalized.split()[0] if " " in normalized else normalized
            vres = ApplicationVerifier.verify_window_open(app_name=proc_name, window_title_keyword=app_name)
            if vres.verified:
                return f"[OPEN_VERIFIED] '{app_name}' launched and verified active. {vres.evidence}"
            elif vres.observed_state and vres.observed_state.get("process_name"):
                return f"[PROCESS_STARTED] Process '{vres.observed_state['process_name']}' is active for '{app_name}'. {vres.details}"
            else:
                return f"[SUCCESS_UNVERIFIED] Launch command sent for '{app_name}'. {vres.details}"
        except Exception as ver_err:
            return f"[SUCCESS_UNVERIFIED] Launch command sent for '{app_name}' (verification note: {ver_err})."
    except Exception as e:
        logger.warning(f"[open_app] Error: {e}")
        return f"[OPEN_FAILED] Failed to open {app_name}: {e}"
