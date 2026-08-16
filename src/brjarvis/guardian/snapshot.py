# guardian/snapshot.py — System & Code Snapshot Manager
"""
Manages pre-upgrade git commits, database backups, and rolling snapshot retention.
"""
from __future__ import annotations

import logging
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.Guardian.Snapshot")

SNAPSHOT_DIR = paths.WORKSPACE_ROOT / "snapshots"


class SnapshotManager:
    """Creates and manages snapshots prior to autonomous changes."""

    @classmethod
    def create_snapshot(cls, tag_prefix: str = "auto_snapshot") -> dict | None:
        """Create a pre-operation git commit tag and database backup snapshot."""
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        snapshot_id = f"{tag_prefix}_{timestamp}"
        snap_path = SNAPSHOT_DIR / snapshot_id
        snap_path.mkdir(parents=True, exist_ok=True)

        # 1. Back up database files if present
        db_files = [paths.MEMORY_ROOT / "workflows.db", paths.MEMORY_ROOT / "conversation_history.db"]
        backed_up = []
        for db_path in db_files:
            if db_path.exists():
                dest = snap_path / db_path.name
                shutil.copy2(db_path, dest)
                backed_up.append(db_path.name)

        # 2. Save git commit hash or git stash tag
        git_hash = None
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                cwd=".",
            )
            if res.returncode == 0:
                git_hash = res.stdout.strip()
                (snap_path / "git_hash.txt").write_text(git_hash, encoding="utf-8")
        except Exception as e:
            logger.exception('Boot critical exception encountered in guardian/snapshot.py')
            raise e
        info = {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "path": str(snap_path),
            "git_hash": git_hash,
            "databases": backed_up,
        }

        # Save metadata
        (snap_path / "metadata.json").write_text(
            json.dumps(info, indent=2), encoding="utf-8"
        )
        cls.prune_old_snapshots(max_count=20)
        return info

    @classmethod
    def prune_old_snapshots(cls, max_count: int = 20):
        """Keep max_count latest snapshots and prune older ones."""
        if not SNAPSHOT_DIR.exists():
            return
        snaps = sorted(
            [d for d in SNAPSHOT_DIR.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
        )
        if len(snaps) > max_count:
            for s in snaps[:-max_count]:
                try:
                    shutil.rmtree(s)
                except Exception as e:
                    logger.exception('Boot critical exception encountered in guardian/snapshot.py')
                    raise e
