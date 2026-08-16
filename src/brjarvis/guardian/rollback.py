# guardian/rollback.py — Automatic Rollback Engine
"""
Automatic Rollback Engine that restores system state on failed healthchecks.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from .snapshot import SNAPSHOT_DIR

logger = logging.getLogger(__name__)


class RollbackEngine:
    """Restores codebase and databases to the last clean snapshot."""

    @classmethod
    def rollback_to_latest(cls) -> dict:
        """Roll back git state and databases to the most recent snapshot."""
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
                    text=True, encoding="utf-8", errors="replace",
                    cwd=".",
                )
                if res.returncode == 0:
                    git_restored = True
            except Exception as e:
                logger.exception('Boot critical exception encountered in guardian/rollback.py')
                raise e
        # 2. Restore Database files
        restored_dbs = []
        for db_name in ["workflows.db", "conversation_history.db"]:
            snap_db = latest_snap / db_name
            if snap_db.exists():
                target_db = Path("memory_db") / db_name
                target_db.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(snap_db, target_db)
                restored_dbs.append(db_name)

        return {
            "success": True,
            "snapshot_id": latest_snap.name,
            "git_restored": git_restored,
            "databases_restored": restored_dbs,
        }
