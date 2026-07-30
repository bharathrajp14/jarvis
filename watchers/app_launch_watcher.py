# watchers/app_launch_watcher.py — Background App Launch Telemetry & Watcher
"""
AppLaunchWatcher continuously monitors process table deltas to detect,
log, and emit events when new applications are started on the OS.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Set
from events.bus import get_event_bus
from actions.app_tracker import log_app_launch

logger = logging.getLogger("JARVIS.AppLaunchWatcher")

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


class AppLaunchWatcher:
    """
    Event-driven process watcher that detects newly spawned applications.
    """

    def __init__(self):
        self.event_bus = get_event_bus()
        self._known_pids: Set[int] = set()
        self._initialized = False
        self._ignore_names = {
            "svchost.exe", "conhost.exe", "cmd.exe", "powershell.exe", "wt.exe",
            "system", "idle", "registry", "smss.exe", "csrss.exe", "wininit.exe",
            "services.exe", "lsass.exe", "taskhostw.exe", "py.exe", "python.exe"
        }

    def initialize_pids(self):
        """Warm up the initial snapshot of active PIDs."""
        if not _PSUTIL_AVAILABLE:
            return
        try:
            self._known_pids = {p.pid for p in psutil.process_iter(['pid'])}
            self._initialized = True
        except Exception as e:
            logger.debug(f"AppLaunchWatcher warm-up error: {e}")

    def check_new_launches(self) -> int:
        """
        Check for newly created processes since the last check.
        Returns the count of newly detected app starts.
        """
        if not _PSUTIL_AVAILABLE:
            return 0

        if not self._initialized:
            self.initialize_pids()
            return 0

        new_count = 0
        current_pids: Set[int] = set()

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
            try:
                pid = proc.info['pid']
                current_pids.add(pid)

                if pid not in self._known_pids:
                    name = proc.info['name'] or f"PID_{pid}"
                    exe = proc.info['exe'] or ""

                    # Skip system daemons / noise
                    if name.lower() not in self._ignore_names:
                        log_app_launch(
                            app_name=name,
                            exe_path=exe,
                            pid=pid,
                            source="system_watcher",
                            details={"create_time": proc.info.get("create_time")}
                        )
                        self.event_bus.publish("app.started", {
                            "app_name": name,
                            "pid": pid,
                            "exe_path": exe
                        })
                        new_count += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        self._known_pids = current_pids
        return new_count


# Global singleton instance
_watcher_instance = AppLaunchWatcher()


def get_app_launch_watcher() -> AppLaunchWatcher:
    return _watcher_instance
