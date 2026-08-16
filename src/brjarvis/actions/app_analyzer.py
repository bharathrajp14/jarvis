# actions/app_analyzer.py — System Application Analyzer for BR-Jarvis
"""
System Application Analyzer for BR-Jarvis.
Scans installed applications across OS platforms (Windows, Linux, macOS)
and inspects active/running processes and application windows.
"""
from __future__ import annotations

import os
import sys
import glob
import logging
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.AppAnalyzer")

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


class SystemAppAnalyzer:
    """
    Analyzer for discovering installed software applications and inspect running system apps.
    """

    def __init__(self):
        self.os_type = platform.system()

    def scan_installed_apps(self) -> List[Dict[str, Any]]:
        """
        Scan and return a list of installed desktop applications on the system.
        Returns a list of dicts: [{'name': ..., 'path': ..., 'version': ..., 'source': ...}]
        """
        apps: List[Dict[str, Any]] = []
        seen_names = set()

        if self.os_type == "Windows":
            apps.extend(self._scan_windows_registry(seen_names))
            apps.extend(self._scan_windows_start_menu(seen_names))
            apps.extend(self._scan_windows_program_files(seen_names))
        elif self.os_type == "Linux":
            apps.extend(self._scan_linux_desktop_files(seen_names))
        elif self.os_type == "Darwin":
            apps.extend(self._scan_mac_applications(seen_names))

        apps.sort(key=lambda x: x["name"].lower())
        return apps

    def _scan_windows_start_menu(self, seen_names: set) -> List[Dict[str, Any]]:
        """Scan Windows Start Menu shortcuts."""
        results = []
        shortcut_dirs = []

        appdata = os.environ.get("APPDATA")
        programdata = os.environ.get("PROGRAMDATA")

        if appdata:
            shortcut_dirs.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        if programdata:
            shortcut_dirs.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        for s_dir in shortcut_dirs:
            if not s_dir.exists():
                continue
            for entry in s_dir.rglob("*"):
                if entry.suffix.lower() in (".lnk", ".url", ".exe"):
                    name = entry.stem
                    # Ignore uninstallers or web links if desired
                    if name.lower() not in seen_names and "uninstall" not in name.lower():
                        seen_names.add(name.lower())
                        results.append({
                            "name": name,
                            "path": str(entry),
                            "version": "N/A",
                            "source": "Start Menu"
                        })
        return results

    def _scan_windows_registry(self, seen_names: set) -> List[Dict[str, Any]]:
        """Scan Windows Registry Uninstall keys."""
        results = []
        if sys.platform != "win32":
            return results

        try:
            import winreg
        except ImportError:
            return results

        keys_to_scan = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hkey, subkey in keys_to_scan:
            try:
                reg_key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
            except OSError:
                continue

            num_subkeys = winreg.QueryInfoKey(reg_key)[0]
            for i in range(num_subkeys):
                try:
                    key_name = winreg.EnumKey(reg_key, i)
                    sub_key = winreg.OpenKey(reg_key, key_name)
                    
                    try:
                        name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                    except OSError:
                        winreg.CloseKey(sub_key)
                        continue

                    if not name or name.lower() in seen_names or "update" in name.lower() or "redistributable" in name.lower():
                        winreg.CloseKey(sub_key)
                        continue

                    seen_names.add(name.lower())

                    try:
                        version, _ = winreg.QueryValueEx(sub_key, "DisplayVersion")
                    except OSError:
                        version = "N/A"

                    try:
                        exe_path, _ = winreg.QueryValueEx(sub_key, "InstallLocation")
                    except OSError:
                        exe_path = ""

                    results.append({
                        "name": str(name),
                        "path": str(exe_path),
                        "version": str(version),
                        "source": "Registry"
                    })
                    winreg.CloseKey(sub_key)
                except OSError:
                    continue

            winreg.CloseKey(reg_key)

        return results

    def _scan_windows_program_files(self, seen_names: set) -> List[Dict[str, Any]]:
        """Scan Program Files folders for executable applications."""
        results = []
        prog_dirs = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LocalAppData") + "\\Programs" if os.environ.get("LocalAppData") else None
        ]

        for p_dir in prog_dirs:
            if not p_dir or not os.path.exists(p_dir):
                continue
            path_obj = Path(p_dir)
            try:
                for sub in path_obj.iterdir():
                    if sub.is_dir() and sub.name.lower() not in seen_names:
                        # Find main executable in sub folder
                        exes = list(sub.glob("*.exe"))
                        if exes:
                            main_exe = next((e for e in exes if e.stem.lower() == sub.name.lower()), exes[0])
                            seen_names.add(sub.name.lower())
                            results.append({
                                "name": sub.name,
                                "path": str(main_exe),
                                "version": "N/A",
                                "source": "Program Files"
                            })
            except Exception as e:
                logger.debug(f"Error scanning directory {p_dir}: {e}")

        return results

    def _scan_linux_desktop_files(self, seen_names: set) -> List[Dict[str, Any]]:
        """Scan Linux .desktop application shortcuts."""
        results = []
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local" / "share" / "applications"
        ]

        for d_dir in desktop_dirs:
            if not d_dir.exists():
                continue
            for d_file in d_dir.glob("*.desktop"):
                try:
                    name = None
                    exec_cmd = None
                    with open(d_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.startswith("Name=") and not name:
                                name = line.strip().split("=", 1)[1]
                            elif line.startswith("Exec=") and not exec_cmd:
                                exec_cmd = line.strip().split("=", 1)[1]
                    if name and name.lower() not in seen_names:
                        seen_names.add(name.lower())
                        results.append({
                            "name": name,
                            "path": exec_cmd or str(d_file),
                            "version": "N/A",
                            "source": ".desktop file"
                        })
                except Exception:
                    pass
        return results

    def _scan_mac_applications(self, seen_names: set) -> List[Dict[str, Any]]:
        """Scan macOS /Applications directory."""
        results = []
        app_dirs = [Path("/Applications"), Path.home() / "Applications"]

        for a_dir in app_dirs:
            if not a_dir.exists():
                continue
            for app in a_dir.glob("*.app"):
                name = app.stem
                if name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    results.append({
                        "name": name,
                        "path": str(app),
                        "version": "N/A",
                        "source": "Applications"
                    })
        return results

    def get_running_apps(self, filter_gui_only: bool = True) -> List[Dict[str, Any]]:
        """
        Inspect all currently running applications / processes on the system.
        """
        running: List[Dict[str, Any]] = []
        if not _PSUTIL_AVAILABLE:
            return running

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time', 'memory_info', 'cpu_percent']):
            try:
                info = proc.info
                name = info['name'] or ""
                exe = info['exe'] or ""
                pid = info['pid']

                # Calculate memory in MB
                mem_mb = 0.0
                if info.get('memory_info'):
                    mem_mb = round(info['memory_info'].rss / (1024 * 1024), 1)

                start_time = info.get('create_time') or 0.0

                # Filter system noise if GUI only requested
                if filter_gui_only:
                    # Common background system daemon noise filter
                    if name.lower() in ("svchost.exe", "system", "idle", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe"):
                        continue

                running.append({
                    "pid": pid,
                    "name": name,
                    "exe_path": exe,
                    "memory_mb": mem_mb,
                    "cpu_percent": info.get('cpu_percent', 0.0),
                    "start_time": start_time,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        running.sort(key=lambda x: x["memory_mb"], reverse=True)
        return running

    def search_apps(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search both installed and running applications by keyword.
        """
        q = query.lower().strip()
        installed = self.scan_installed_apps()
        running = self.get_running_apps(filter_gui_only=False)

        matching_installed = [a for a in installed if q in a["name"].lower() or q in a["path"].lower()]
        matching_running = [r for r in running if q in r["name"].lower() or q in r["exe_path"].lower()]

        return {
            "query": query,
            "installed_matches": matching_installed,
            "running_matches": matching_running
        }


# Global singleton instance
_analyzer = SystemAppAnalyzer()


def get_app_analyzer() -> SystemAppAnalyzer:
    return _analyzer
