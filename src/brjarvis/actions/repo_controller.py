# actions/repo_controller.py — Autonomous Git Repository Action Controller for JARVIS MK37
"""
Autonomous action controller for git repository workflows, diff inspection, branch management,
and automated commit operations.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class RepoControllerAction:
    """Git Repository Autonomous Controller."""

    def __init__(self, repo_dir: str | Path = "."):
        self.repo_dir = Path(repo_dir).resolve()

    def _exec_git(self, cmd: list[str]) -> tuple[int, str]:
        try:
            res = subprocess.run(
                ["git"] + cmd,
                cwd=str(self.repo_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=20
            )
            return res.returncode, res.stdout.strip()
        except Exception as e:
            return -1, str(e)

    def get_summary(self) -> str:
        code, branch_out = self._exec_git(["branch", "--show-current"])
        code, status_out = self._exec_git(["status", "--short"])
        lines = status_out.splitlines() if status_out else []
        return (
            f"🌿 Repository: {self.repo_dir.name}\n"
            f"● Current Branch: {branch_out or 'HEAD'}\n"
            f"● Modified Files: {len(lines)}\n"
            f"● Changes Preview:\n" + ("\n".join(lines[:10]) if lines else "  Clean working tree.")
        )

    def auto_commit(self, commit_prefix: str = "feat") -> str:
        code, diff_out = self._exec_git(["diff", "--stat"])
        if not diff_out:
            code, status_out = self._exec_git(["status", "--short"])
            if not status_out:
                return "ℹ️ No changes to commit."

        self._exec_git(["add", "-A"])
        msg = f"{commit_prefix}: automated updates by BR JARVIS MK37"
        code, out = self._exec_git(["commit", "-m", msg])
        if code == 0:
            return f"✅ Auto-commit succeeded: '{msg}'\n{out}"
        return f"⚠️ Commit failed or nothing to commit:\n{out}"


def inspect_repository(repo_path: str = ".") -> str:
    action = RepoControllerAction(repo_path)
    return action.get_summary()
