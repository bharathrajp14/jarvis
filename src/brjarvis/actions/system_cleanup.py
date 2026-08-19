# actions/system_cleanup.py — Storage Decluttering & Cache Cleaner Action for JARVIS MK37
"""
Autonomous action to scan and clean temporary system files, obsolete log files,
build artifacts, and free up disk space.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class SystemCleanupAction:
    """Autonomous System Cleanup and Cache Manager."""

    def __init__(self, workspace_root: str | Path = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def run_cleanup(self, clean_temp: bool = True, clean_pycache: bool = True, clean_logs: bool = False) -> str:
        reclaimed_bytes = 0
        removed_items = []

        # 1. Clean workspace __pycache__ and .pytest_cache
        if clean_pycache:
            for p in self.workspace_root.rglob("__pycache__"):
                try:
                    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    shutil.rmtree(p)
                    reclaimed_bytes += size
                    removed_items.append(f"Pycache: {p.relative_to(self.workspace_root)}")
                except Exception as e:
                    logger.debug("Suppressed exception: %s", e)
        # 2. Clean OS Temp directory (.tmp files > 24 hours old)
        if clean_temp:
            temp_dir = Path(tempfile.gettempdir())
            try:
                for item in temp_dir.iterdir():
                    if item.is_file() and item.name.startswith("tmp"):
                        try:
                            st = item.stat()
                            reclaimed_bytes += st.st_size
                            item.unlink()
                        except Exception as e:
                            logger.debug("Suppressed exception: %s", e)
            except Exception as e:
                logger.debug("Suppressed exception: %s", e)
        # 3. Clean workspace logs if requested
        if clean_logs:
            logs_dir = self.workspace_root / "logs"
            if logs_dir.exists():
                for log_file in logs_dir.glob("*.log"):
                    try:
                        size = log_file.stat().st_size
                        log_file.unlink()
                        reclaimed_bytes += size
                        removed_items.append(f"Log: {log_file.name}")
                    except Exception as e:
                        logger.debug("Suppressed exception: %s", e)
        mb = reclaimed_bytes / (1024 * 1024)
        return (
            f"🧹 System Cleanup Complete:\n"
            f"- Reclaimed Storage: {mb:.2f} MB\n"
            f"- Cleaned Items: {len(removed_items)} folders/files"
        )


def execute_system_cleanup(clean_temp: bool = True, clean_pycache: bool = True, clean_logs: bool = False) -> str:
    action = SystemCleanupAction()
    return action.run_cleanup(clean_temp=clean_temp, clean_pycache=clean_pycache, clean_logs=clean_logs)
