# guardian/rollback.py — Automatic Rollback Engine
"""
Automatic Rollback Engine that restores system state on failed healthchecks.
"""

from __future__ import annotations

import logging
import subprocess

from .snapshot import SNAPSHOT_DIR

logger = logging.getLogger(__name__)


class RollbackEngine:
    """Restores codebase and databases to the last clean snapshot."""

    @classmethod
    def rollback_to_latest(cls) -> dict:
        """Roll back git state and databases to the most recent snapshot."""
        from brjarvis.core.paths import paths

        from .snapshot import SnapshotManager

        if not SNAPSHOT_DIR.exists():
            return {"success": False, "reason": "No snapshots directory found"}

        snaps = sorted(
            [d for d in SNAPSHOT_DIR.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
        )
        if not snaps:
            return {"success": False, "reason": "No snapshots available"}

        latest_snap = snaps[-1]

        # 1. Restore Git state if hash present
        git_hash_file = latest_snap / "git_hash.txt"
        git_restored = False
        if git_hash_file.exists():
            git_hash = git_hash_file.read_text(encoding="utf-8").strip()
            try:
                res = subprocess.run(
                    ["git", "checkout", git_hash],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(paths.PROJECT_ROOT),
                )
                if res.returncode == 0:
                    git_restored = True
            except Exception as e:
                logger.warning("[Rollback] Git checkout to %s failed: %s", git_hash, e)

        # 2. Restore Database files using SnapshotManager
        db_restored = SnapshotManager.restore_snapshot(latest_snap.name)

        return {
            "success": True,
            "snapshot_id": latest_snap.name,
            "git_restored": git_restored,
            "databases_restored": db_restored,
        }
