# agent/scratchpad.py — Antigravity-Style Dynamic Scratchpad Engine
"""
Scratchpad Engine for BR JARVIS.
Provides temporary workspace script execution, scratch memory context,
and transient data storage in ./scratch/.
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional


def _get_scratch_dir() -> Path:
    base = Path(__file__).resolve().parent.parent
    scratch_dir = base / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir


class ScratchpadManager:
    """Manages temporary scratch space files, execution, and live reasoning notes."""

    _instance: Optional[ScratchpadManager] = None

    def __init__(self):
        self.dir = _get_scratch_dir()
        self._notes: List[str] = []

    @classmethod
    def get_instance(cls) -> ScratchpadManager:
        if cls._instance is None:
            cls._instance = ScratchpadManager()
        return cls._instance

    def add_note(self, note: str) -> str:
        """Add a scratch note to the active scratchpad buffer."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {note}"
        self._notes.append(entry)
        return f"Added scratch note #{len(self._notes)}: '{note[:60]}...'"

    def get_notes(self) -> List[str]:
        """Retrieve active scratch notes."""
        return list(self._notes)

    def write_file(self, filename: str, content: str) -> str:
        """Write content to a file in the scratch directory."""
        # Sanitize filename
        clean_name = Path(filename).name
        target = self.dir / clean_name
        target.write_text(content, encoding="utf-8")
        return f"Scratchpad file created: {target.resolve()} ({len(content)} bytes)"

    def read_file(self, filename: str) -> str:
        """Read content from a scratch file."""
        clean_name = Path(filename).name
        target = self.dir / clean_name
        if not target.exists():
            return f"Error: Scratch file '{clean_name}' does not exist in {self.dir}"
        return target.read_text(encoding="utf-8", errors="replace")

    def list_files(self) -> List[Dict[str, Any]]:
        """List all files currently in the scratch directory."""
        files = []
        for p in self.dir.glob("*"):
            if p.is_file():
                stat = p.stat()
                files.append({
                    "name": p.name,
                    "path": str(p.resolve()),
                    "size_bytes": stat.st_size,
                    "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                })
        return files

    def clear(self) -> str:
        """Clear scratch notes and non-essential scratch files."""
        self._notes.clear()
        count = 0
        for p in self.dir.glob("*"):
            if p.is_file():
                try:
                    p.unlink()
                    count += 1
                except Exception as e:
                    if 'logger' in globals() or 'logger' in locals():
                        logger.debug('Suppressed exception: %s', e)
                    else:
                        import logging
                        logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        return f"Scratchpad cleared: {count} files removed, notes reset."

    def eval_script(self, target: str, language: str = "python", timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a script or raw code in the scratch environment and return results.
        Language options: 'python', 'node', 'powershell', 'bash'.
        """
        # If target looks like raw code, save it as a temporary script first
        if "\n" in target or len(target) > 80 or not (self.dir / target).exists():
            ext = ".py" if language == "python" else ".js" if language == "node" else ".ps1"
            script_name = f"scratch_eval_{int(time.time())}{ext}"
            script_path = self.dir / script_name
            script_path.write_text(target, encoding="utf-8")
        else:
            script_path = self.dir / Path(target).name

        if not script_path.exists():
            return {
                "success": False,
                "error": f"Script target '{target}' not found.",
                "stdout": "",
                "stderr": "",
                "execution_ms": 0,
            }

        lang = language.lower()
        if lang in ("py", "python"):
            cmd = [sys.executable, str(script_path)]
        elif lang in ("js", "node", "nodejs"):
            cmd = ["node", str(script_path)]
        elif lang in ("ps1", "powershell"):
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        elif lang in ("sh", "bash"):
            cmd = ["bash", str(script_path)]
        else:
            cmd = [sys.executable, str(script_path)]

        t_start = time.monotonic()
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            dur_ms = int((time.monotonic() - t_start) * 1000)
            return {
                "success": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "execution_ms": dur_ms,
                "script_path": str(script_path.resolve()),
            }
        except subprocess.TimeoutExpired:
            dur_ms = int((time.monotonic() - t_start) * 1000)
            return {
                "success": False,
                "error": f"Execution timed out after {timeout} seconds.",
                "stdout": "",
                "stderr": f"Timeout expired ({timeout}s)",
                "execution_ms": dur_ms,
                "script_path": str(script_path.resolve()),
            }
        except Exception as e:
            dur_ms = int((time.monotonic() - t_start) * 1000)
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
                "execution_ms": dur_ms,
                "script_path": str(script_path.resolve()),
            }


def get_scratchpad() -> ScratchpadManager:
    return ScratchpadManager.get_instance()
