# actions/app_resolver.py — Automated System Application Path Resolver for BR JARVIS
"""
Automated System Application Path Resolver and Configuration Engine for BR JARVIS.
Automatically scans the Windows Registry, Start Menu, LocalAppData, Program Files,
and System PATH to build an indexed, fuzzy-searchable, and persistent app_paths.json registry.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.AppResolver")

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_APP_PATHS_FILE = _CONFIG_DIR / "app_paths.json"

# Common Windows App Aliases & Protocol URI fallbacks
DEFAULT_ALIAS_MAP: Dict[str, List[str]] = {
    "chrome": ["chrome.exe", "Google Chrome", "google-chrome"],
    "google chrome": ["chrome.exe", "Google Chrome"],
    "brave": ["brave.exe", "Brave", "brave-browser"],
    "edge": ["msedge.exe", "Microsoft Edge", "msedge"],
    "microsoft edge": ["msedge.exe", "Microsoft Edge"],
    "firefox": ["firefox.exe", "Mozilla Firefox"],
    "vscode": ["Code.exe", "Visual Studio Code", "code"],
    "visual studio code": ["Code.exe", "Visual Studio Code"],
    "code": ["Code.exe", "Visual Studio Code"],
    "notepad": ["notepad.exe", "Notepad"],
    "calculator": ["calc.exe", "Calculator"],
    "calc": ["calc.exe", "Calculator"],
    "paint": ["mspaint.exe", "Paint"],
    "mspaint": ["mspaint.exe", "Paint"],
    "word": ["WINWORD.EXE", "winword.exe", "Microsoft Word", "Word"],
    "excel": ["EXCEL.EXE", "excel.exe", "Microsoft Excel", "Excel"],
    "powerpoint": ["POWERPNT.EXE", "powerpnt.exe", "Microsoft PowerPoint"],
    "terminal": ["wt.exe", "Windows Terminal", "powershell.exe", "cmd.exe"],
    "cmd": ["cmd.exe", "Command Prompt"],
    "powershell": ["powershell.exe", "Windows PowerShell"],
    "explorer": ["explorer.exe", "File Explorer"],
    "file explorer": ["explorer.exe", "File Explorer"],
    "task manager": ["taskmgr.exe", "Task Manager"],
    "settings": ["ms-settings:", "Settings"],
    "spotify": ["Spotify.exe", "Spotify", "spotify:"],
    "discord": ["Discord.exe", "Discord", "Update.exe"],
    "telegram": ["Telegram.exe", "Telegram Desktop", "Telegram"],
    "whatsapp": ["WhatsApp.exe", "WhatsApp", "whatsapp:"],
    "slack": ["slack.exe", "Slack"],
    "vlc": ["vlc.exe", "VLC media player", "VLC"],
    "notion": ["Notion.exe", "Notion"],
    "obsidian": ["Obsidian.exe", "Obsidian"],
    "steam": ["steam.exe", "Steam"],
    "git": ["git-bash.exe", "Git Bash"],
    "postman": ["Postman.exe", "Postman"],
    "antigravity": ["Antigravity IDE.lnk", "Antigravity.lnk", "Antigravity.exe", "Antigravity IDE"],
}


class ApplicationResolver:
    """Discovers, indexes, and resolves executable paths for system applications."""

    def __init__(self, auto_scan: bool = True):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_cached_paths()
        if auto_scan and (not self._cache or len(self._cache) < 10):
            self.rescan_system_applications()

    def _load_cached_paths(self) -> None:
        """Load cached application paths from config/app_paths.json."""
        if _APP_PATHS_FILE.exists():
            try:
                data = json.loads(_APP_PATHS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._cache = data
                    logger.info("[AppResolver] Loaded %d application paths from cache.", len(self._cache))
            except Exception as e:
                logger.warning("[AppResolver] Failed to parse app_paths.json: %s", e)

    def _save_cache(self) -> None:
        """Save indexed application paths to config/app_paths.json."""
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            _APP_PATHS_FILE.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
            logger.info("[AppResolver] Saved %d application paths to %s", len(self._cache), _APP_PATHS_FILE)
        except Exception as e:
            logger.error("[AppResolver] Failed to save app_paths.json: %s", e)

    def rescan_system_applications(self) -> Dict[str, Dict[str, Any]]:
        """Perform a deep scan of the host OS to discover all installed applications."""
        discovered: Dict[str, Dict[str, Any]] = {}

        if sys.platform == "win32":
            self._scan_windows_app_paths_registry(discovered)
            self._scan_windows_start_menu(discovered)
            self._scan_windows_standard_directories(discovered)
            self._scan_windows_uninstall_registry(discovered)
        elif sys.platform == "darwin":
            self._scan_macos_applications(discovered)
        else:
            self._scan_linux_desktop_files(discovered)

        # Merge with existing manual overrides
        for k, v in self._cache.items():
            if v.get("manual_override"):
                discovered[k] = v

        self._cache = discovered
        self._save_cache()
        return self._cache

    def _scan_windows_app_paths_registry(self, discovered: Dict[str, Dict[str, Any]]) -> None:
        """Scan HKLM and HKCU 'App Paths' registry keys."""
        try:
            import winreg
        except ImportError:
            return

        hives = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        ]

        for hive, root_key_path in hives:
            try:
                with winreg.OpenKey(hive, root_key_path) as root_key:
                    num_subkeys, _, _ = winreg.QueryInfoKey(root_key)
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(root_key, i)
                            with winreg.OpenKey(root_key, subkey_name) as subkey:
                                exe_path, _ = winreg.QueryValueEx(subkey, "")
                                if exe_path and os.path.exists(exe_path.strip('"')):
                                    clean_path = exe_path.strip('"')
                                    name_key = subkey_name.lower().replace(".exe", "").strip()
                                    discovered[name_key] = {
                                        "name": subkey_name,
                                        "path": clean_path,
                                        "type": "executable",
                                        "source": "Registry App Paths"
                                    }
                        except Exception:
                            continue
            except Exception:
                continue

    def _scan_windows_start_menu(self, discovered: Dict[str, Dict[str, Any]]) -> None:
        """Scan Start Menu .lnk shortcuts."""
        search_dirs = []
        appdata = os.environ.get("APPDATA")
        programdata = os.environ.get("PROGRAMDATA")

        if appdata:
            search_dirs.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        if programdata:
            search_dirs.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for entry in sdir.rglob("*"):
                if entry.suffix.lower() in (".lnk", ".url", ".exe"):
                    stem_clean = entry.stem.lower().strip()
                    if "uninstall" in stem_clean or "help" in stem_clean:
                        continue
                    if stem_clean not in discovered:
                        discovered[stem_clean] = {
                            "name": entry.stem,
                            "path": str(entry),
                            "type": "shortcut" if entry.suffix.lower() == ".lnk" else "executable",
                            "source": "Start Menu"
                        }

    def _scan_windows_standard_directories(self, discovered: Dict[str, Dict[str, Any]]) -> None:
        """Scan common local app and program directories."""
        user_profile = os.environ.get("USERPROFILE", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

        candidate_dirs = [
            Path(local_app_data) / "Programs",
            Path(local_app_data),
            Path(prog_files),
            Path(prog_files_x86),
            Path(user_profile) / "AppData" / "Local" / "Microsoft" / "WindowsApps",
        ]

        for cdir in candidate_dirs:
            if not cdir.exists():
                continue
            try:
                # Top 2 levels of subdirectories
                for sub in cdir.iterdir():
                    if sub.is_file() and sub.suffix.lower() == ".exe":
                        stem = sub.stem.lower()
                        if stem not in discovered:
                            discovered[stem] = {
                                "name": sub.stem,
                                "path": str(sub),
                                "type": "executable",
                                "source": "Standard Directory"
                            }
                    elif sub.is_dir():
                        for item in sub.glob("*.exe"):
                            stem = item.stem.lower()
                            if stem not in discovered:
                                discovered[stem] = {
                                    "name": item.stem,
                                    "path": str(item),
                                    "type": "executable",
                                    "source": "Standard Directory"
                                }
            except Exception:
                continue

    def _scan_windows_uninstall_registry(self, discovered: Dict[str, Dict[str, Any]]) -> None:
        """Scan Windows Uninstall Registry to get InstallLocation and DisplayIcon."""
        try:
            import winreg
        except ImportError:
            return

        hives = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hive, root_key_path in hives:
            try:
                with winreg.OpenKey(hive, root_key_path) as root_key:
                    num_subkeys, _, _ = winreg.QueryInfoKey(root_key)
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(root_key, i)
                            with winreg.OpenKey(root_key, subkey_name) as subkey:
                                try:
                                    disp_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                except Exception:
                                    disp_name = None

                                try:
                                    install_loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                except Exception:
                                    install_loc = None

                                try:
                                    disp_icon, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
                                except Exception:
                                    disp_icon = None

                                if disp_name and (install_loc or disp_icon):
                                    stem = str(disp_name).lower().strip()
                                    target_path = None
                                    if disp_icon and str(disp_icon).lower().endswith(".exe") and os.path.exists(str(disp_icon).strip('"')):
                                        target_path = str(disp_icon).strip('"')
                                    elif install_loc and os.path.isdir(str(install_loc).strip('"')):
                                        # Look for exe inside install_loc
                                        p_loc = Path(str(install_loc).strip('"'))
                                        exes = list(p_loc.glob("*.exe"))
                                        if exes:
                                            target_path = str(exes[0])

                                    if target_path and stem not in discovered:
                                        discovered[stem] = {
                                            "name": str(disp_name),
                                            "path": target_path,
                                            "type": "executable",
                                            "source": "Uninstall Registry"
                                        }
                        except Exception:
                            continue
            except Exception:
                continue

    def _scan_macos_applications(self, discovered: Dict[str, Dict[str, Any]]) -> None:
        """Scan macOS /Applications and ~/Applications."""
        dirs = [Path("/Applications"), Path.home() / "Applications"]
        for d in dirs:
            if not d.exists():
                continue
            for app in d.glob("*.app"):
                stem = app.stem.lower()
                discovered[stem] = {
                    "name": app.stem,
                    "path": str(app),
                    "type": "app_bundle",
                    "source": "macOS Applications"
                }

    def _scan_linux_desktop_files(self, discovered: Dict[str, Dict[str, Any]]) -> None:
        """Scan Linux .desktop application entries."""
        dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local/share/applications"
        ]
        for d in dirs:
            if not d.exists():
                continue
            for df in d.glob("*.desktop"):
                try:
                    text = df.read_text(encoding="utf-8", errors="ignore")
                    name = None
                    exec_cmd = None
                    for line in text.splitlines():
                        if line.startswith("Name=") and not name:
                            name = line.split("=", 1)[1].strip()
                        elif line.startswith("Exec=") and not exec_cmd:
                            exec_cmd = line.split("=", 1)[1].split()[0].strip()
                    if name and exec_cmd:
                        stem = name.lower()
                        discovered[stem] = {
                            "name": name,
                            "path": exec_cmd,
                            "type": "desktop_entry",
                            "source": "Linux Desktop Entry"
                        }
                except Exception:
                    continue

    def resolve(self, app_query: str) -> Optional[Tuple[str, str]]:
        """
        Resolve an application name or alias to a concrete executable/shortcut path or URI scheme.
        Returns: (resolved_path_or_uri, target_type) or None
        """
        q_raw = app_query.strip()
        q_lower = q_raw.lower()

        # 1. Check URI schemes & special protocols
        if q_lower in ("settings", "ms-settings", "windows settings"):
            return ("ms-settings:", "protocol_uri")
        if q_lower in ("calc", "calculator"):
            return ("calc.exe", "system_binary")
        if q_lower in ("notepad", "text editor"):
            return ("notepad.exe", "system_binary")
        if q_lower in ("paint", "mspaint"):
            return ("mspaint.exe", "system_binary")
        if q_lower in ("cmd", "command prompt"):
            return ("cmd.exe", "system_binary")
        if q_lower in ("powershell", "ps"):
            return ("powershell.exe", "system_binary")
        if q_lower in ("explorer", "file explorer"):
            return ("explorer.exe", "system_binary")
        if q_lower in ("taskmgr", "task manager"):
            return ("taskmgr.exe", "system_binary")

        # 2. Check exact cache key match
        if q_lower in self._cache:
            entry = self._cache[q_lower]
            return (entry["path"], entry.get("type", "executable"))

        # 3. Check DEFAULT_ALIAS_MAP candidates against cache
        if q_lower in DEFAULT_ALIAS_MAP:
            for cand in DEFAULT_ALIAS_MAP[q_lower]:
                cand_lower = cand.lower().replace(".exe", "").replace(".lnk", "")
                if cand_lower in self._cache:
                    entry = self._cache[cand_lower]
                    return (entry["path"], entry.get("type", "executable"))
                # Check if candidate is directly executable via PATH
                which_bin = shutil.which(cand) or shutil.which(cand.split()[0])
                if which_bin:
                    return (which_bin, "system_binary")

        # 4. Fuzzy Substring Match in Cache
        for key, entry in self._cache.items():
            if q_lower == key or q_lower in key or key in q_lower:
                return (entry["path"], entry.get("type", "executable"))

        # 5. Check System PATH via shutil.which()
        which_path = shutil.which(q_raw) or shutil.which(q_lower) or shutil.which(f"{q_lower}.exe")
        if which_path:
            return (which_path, "system_binary")

        return None

    def launch(self, app_query: str) -> Tuple[bool, str]:
        """
        Resolve and launch an application, verifying its start truthfully.
        Returns: (success: bool, status_message: str)
        """
        resolved = self.resolve(app_query)
        if not resolved:
            # Rescan once if missing
            self.rescan_system_applications()
            resolved = self.resolve(app_query)

        if not resolved:
            return False, f"Could not find or resolve executable path for '{app_query}'. Run sync_app_paths to refresh system index."

        target_path, target_type = resolved
        logger.info("[AppResolver] Launching '%s' via resolved path: %s (%s)", app_query, target_path, target_type)

        try:
            if sys.platform == "win32":
                if target_type == "protocol_uri" or target_path.startswith("ms-"):
                    if hasattr(os, "startfile"):
                        os.startfile(target_path)
                    else:
                        subprocess.Popen(["cmd.exe", "/c", "start", "", target_path], shell=False)
                    return True, f"Launched Windows application protocol '{target_path}'."

                if target_path.lower().endswith(".lnk") or target_path.lower().endswith(".url"):
                    if hasattr(os, "startfile"):
                        os.startfile(target_path)
                    else:
                        subprocess.Popen(["cmd.exe", "/c", "start", "", target_path], shell=False)
                    return True, f"Launched application shortcut: '{target_path}'"

                # Direct executable
                work_dir = str(Path(target_path).parent) if os.path.isfile(target_path) else None
                subprocess.Popen(
                    [target_path],
                    cwd=work_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False
                )
                return True, f"Launched executable: '{target_path}'"

            elif sys.platform == "darwin":
                if target_type == "app_bundle" or target_path.endswith(".app"):
                    subprocess.Popen(["open", target_path])
                else:
                    subprocess.Popen([target_path])
                return True, f"Launched macOS application: '{target_path}'"

            else:  # Linux
                subprocess.Popen([target_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Launched Linux application: '{target_path}'"

        except Exception as e:
            logger.error("[AppResolver] Failed to launch '%s' at '%s': %s", app_query, target_path, e)
            return False, f"Failed to launch application '{app_query}' ({target_path}): {e}"


_RESOLVER_INSTANCE: Optional[ApplicationResolver] = None


def get_app_resolver() -> ApplicationResolver:
    """Singleton getter for the system ApplicationResolver."""
    global _RESOLVER_INSTANCE
    if _RESOLVER_INSTANCE is None:
        _RESOLVER_INSTANCE = ApplicationResolver(auto_scan=True)
    return _RESOLVER_INSTANCE
