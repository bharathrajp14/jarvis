# skills/hot_reload.py — Dynamic Skill Auto-Discovery & Hot Reload Engine
"""
Dynamic Skill Hot-Reload Engine for BR JARVIS.
Monitors skills/ and .agents/skills directories to hot-reload new user-invocable skills
at runtime without requiring assistant restart.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SkillHotReloader:
    """Runtime observer for dynamic skill hot-reloading."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path(__file__).resolve().parent.parent
        self.skills_dir = self.workspace_root / "skills"
        self.agent_skills_dir = self.workspace_root / ".agents" / "skills"
        self._last_scan_mtime: float = 0.0
        self._active_skills_cache: List[Dict[str, Any]] = []

    def scan_and_reload(self) -> List[Dict[str, Any]]:
        """Scan skills directories and reload skill definitions if files changed."""
        current_max_mtime = 0.0
        candidate_files: List[Path] = []

        for s_dir in (self.skills_dir, self.agent_skills_dir):
            if s_dir.exists():
                for root, _, files in os.walk(s_dir):
                    for f in files:
                        if f.endswith(".md"):
                            fp = Path(root) / f
                            candidate_files.append(fp)
                            try:
                                current_max_mtime = max(current_max_mtime, fp.stat().st_mtime)
                            except Exception as e:
                                logger.debug('Suppressed exception: %s', e)
        if current_max_mtime > self._last_scan_mtime or not self._active_skills_cache:
            self._last_scan_mtime = current_max_mtime
            self._active_skills_cache = self._parse_skills(candidate_files)

        return self._active_skills_cache

    def _parse_skills(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """Parse skill metadata from markdown headers."""
        skills = []
        for fp in file_paths:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                name = fp.parent.name if fp.name == "SKILL.md" else fp.stem
                skills.append({
                    "name": name,
                    "path": str(fp),
                    "size_bytes": len(content),
                })
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
        return skills
