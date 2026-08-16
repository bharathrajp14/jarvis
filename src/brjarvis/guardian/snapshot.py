# guardian/snapshot.py — System & Code Snapshot Manager
"""
Manages pre-upgrade git commits, database backups, and rolling snapshot retention.
Supports canonical database backups (SQLite WAL), lessons, and task state.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.Guardian.Snapshot")

SNAPSHOT_DIR = paths.WORKSPACE_ROOT / "snapshots"


class SnapshotManager:
    """Creates, manages, and restores snapshots prior to autonomous changes."""

    @classmethod
    def create_snapshot(cls, tag_prefix: str = "auto_snapshot") -> Dict[str, Any]:
        """Create a pre-operation git commit tag and database backup snapshot."""
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        snapshot_id = f"{tag_prefix}_{timestamp}"
        snap_path = SNAPSHOT_DIR / snapshot_id
        snap_path.mkdir(parents=True, exist_ok=True)

        # 1. Back up database files if present (canonical, memory, workflows)
        db_files = [
            paths.STATE_ROOT / "jarvis_canonical.db",
            paths.STATE_ROOT / "jarvis_canonical.db-wal",
            paths.MEMORY_ROOT / "lessons.db",
            paths.MEMORY_ROOT / "experience_replay.db",
            paths.MEMORY_ROOT / "workflows.db",
            paths.MEMORY_ROOT / "conversation_history.db",
        ]
        backed_up = []
        for db_path in db_files:
            if db_path.exists():
                dest = snap_path / db_path.name
                try:
                    shutil.copy2(db_path, dest)
                    backed_up.append(db_path.name)
                except Exception as e:
                    logger.warning("[Snapshot] Could not backup %s: %s", db_path.name, e)

        # 2. Save git commit hash or git stash tag safely
        git_hash = None
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                cwd=str(paths.WORKSPACE_ROOT),
                timeout=5.0,
            )
            if res.returncode == 0:
                git_hash = res.stdout.strip()
                (snap_path / "git_hash.txt").write_text(git_hash, encoding="utf-8")
        except Exception as e:
            logger.debug("[Snapshot] Git revision check notice: %s", e)

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
        logger.info("📸 Created system snapshot: %s (%d databases backed up)", snapshot_id, len(backed_up))
        return info

    @classmethod
    def restore_snapshot(cls, snapshot_id: str) -> bool:
        """Restore databases and state from an existing snapshot."""
        snap_path = SNAPSHOT_DIR / snapshot_id
        if not snap_path.exists():
            logger.error("[Snapshot] Snapshot directory '%s' does not exist", snapshot_id)
            return False

        meta_file = snap_path / "metadata.json"
        if not meta_file.exists():
            logger.error("[Snapshot] Missing metadata.json in snapshot '%s'", snapshot_id)
            return False

        try:
            info = json.loads(meta_file.read_text(encoding="utf-8"))
            for db_name in info.get("databases", []):
                src = snap_path / db_name
                if src.exists():
                    if "canonical" in db_name:
                        target = paths.STATE_ROOT / db_name
                    else:
                        target = paths.MEMORY_ROOT / db_name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
                    logger.info("[Snapshot] Restored database: %s", db_name)
            return True
        except Exception as e:
            logger.error("[Snapshot] Failed to restore snapshot '%s': %s", snapshot_id, e)
            return False

    @classmethod
    def list_snapshots(cls) -> List[Dict[str, Any]]:
        """List all available snapshots ordered from newest to oldest."""
        if not SNAPSHOT_DIR.exists():
            return []
        results = []
        for d in sorted(SNAPSHOT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if d.is_dir():
                meta_file = d / "metadata.json"
                if meta_file.exists():
                    try:
                        results.append(json.loads(meta_file.read_text(encoding="utf-8")))
                    except Exception:
                        pass
        return results

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
                    logger.debug("[Snapshot] Could not prune old snapshot: %s", e)
