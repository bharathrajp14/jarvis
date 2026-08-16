# src/brjarvis/core/paths.py — Canonical Centralized Path Engine for BR JARVIS MK40.2+
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def find_project_root() -> Path:
    """Deterministically locate the root directory of the BR JARVIS repository."""
    if os.environ.get("JARVIS_PROJECT_ROOT"):
        p = Path(os.environ["JARVIS_PROJECT_ROOT"]).resolve()
        if p.exists():
            return p

    curr = Path(__file__).resolve().parent
    for parent in [curr] + list(curr.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists() or (parent / "start.py").exists():
            return parent

    return Path(__file__).resolve().parent.parent.parent.parent


def find_python_executable(root: Optional[Path] = None) -> Path:
    """
    Deterministically resolve the canonical Python interpreter with precedence:
      1. BR_JARVIS_PYTHON environment override
      2. Project .venv (PROJECT_ROOT/.venv/Scripts/python.exe on Windows, bin/python on POSIX)
      3. Repository-local virtualenv/interpreters
      4. sys.executable
    """
    import sys
    if os.environ.get("BR_JARVIS_PYTHON"):
        override = Path(os.environ["BR_JARVIS_PYTHON"]).resolve()
        if override.exists():
            return override

    proj_root = root or find_project_root()
    venv_dir = proj_root / ".venv"
    if venv_dir.exists():
        if sys.platform == "win32":
            candidates = [
                venv_dir / "Scripts" / "python.exe",
                venv_dir / "python.exe",
            ]
        else:
            candidates = [
                venv_dir / "bin" / "python3",
                venv_dir / "bin" / "python",
            ]
        for cand in candidates:
            if cand.exists():
                return cand.resolve()

    return Path(sys.executable).resolve()


def ensure_canonical_python() -> None:
    """
    If the current process was started with a non-project Python interpreter
    (e.g. system Python 3.14 instead of the project .venv Python 3.12),
    automatically re-exec with the project .venv interpreter to guarantee
    clean runtime isolation and prevent user-site package pollution.
    """
    import subprocess
    import sys

    target = find_python_executable()
    current = Path(sys.executable).resolve()
    if target.exists() and target != current:
        if os.environ.get("_BR_JARVIS_REEXEC") != "1":
            env = os.environ.copy()
            env["_BR_JARVIS_REEXEC"] = "1"
            cmd = [str(target)] + sys.argv
            res = subprocess.run(cmd, env=env)
            sys.exit(res.returncode)


class PathManager:
    """Canonical Path Contract and Workspace Lifecycle Manager for BR JARVIS MK40.2+."""

    _instance: Optional[PathManager] = None

    def __init__(self, root: Optional[Path] = None):
        self.PROJECT_ROOT = (root or find_project_root()).resolve()
        self.PYTHON_EXECUTABLE = find_python_executable(self.PROJECT_ROOT)
        self.VENV_DIR = self.PROJECT_ROOT / ".venv"
        self.DOTENV_FILE = self.PROJECT_ROOT / ".env"
        self.SOURCE_ROOT = self.PROJECT_ROOT / "src" / "brjarvis"
        self.APPS_ROOT = self.PROJECT_ROOT / "apps"
        self.CONFIG_ROOT = self.PROJECT_ROOT / "config"
        self.DOCS_ROOT = self.PROJECT_ROOT / "docs"
        self.TEST_ROOT = self.PROJECT_ROOT / "tests"
        self.SCRIPTS_ROOT = self.PROJECT_ROOT / "scripts"
        self.ASSETS_ROOT = self.PROJECT_ROOT / "assets"

        # Runtime Data Directories
        runtime_env = os.environ.get("JARVIS_RUNTIME_DIR")
        self.RUNTIME_ROOT = Path(runtime_env).resolve() if runtime_env else (self.PROJECT_ROOT / "runtime")
        self.ARTIFACT_ROOT = self.RUNTIME_ROOT / "artifacts"
        self.LOG_ROOT = Path(os.environ.get("JARVIS_LOG_DIR", str(self.RUNTIME_ROOT / "logs"))).resolve()
        self.CAPTURE_ROOT = self.RUNTIME_ROOT / "captures"
        self.REPORT_ROOT = self.RUNTIME_ROOT / "reports"
        self.TEMP_ROOT = self.RUNTIME_ROOT / "temporary"
        self.STATE_ROOT = self.RUNTIME_ROOT / "state"
        self.MEMORY_ROOT = self.STATE_ROOT / "memory_db"

        # User Workspace Directories
        ws_env = os.environ.get("JARVIS_WORKSPACE_DIR")
        self.WORKSPACE_ROOT = Path(ws_env).resolve() if ws_env else (self.PROJECT_ROOT / "workspace")
        self.DOCUMENTS_DIR = self.WORKSPACE_ROOT / "documents"
        self.RESUMES_DIR = self.WORKSPACE_ROOT / "resumes"
        self.CAREER_DIR = self.WORKSPACE_ROOT / "career"
        self.PROJECTS_DIR = self.WORKSPACE_ROOT / "projects"
        self.USER_DATA_DIR = self.WORKSPACE_ROOT / "user-data"

        # Backward compatibility aliases
        self.BASE_DIR = self.PROJECT_ROOT
        self.WORKSPACE_DIR = self.WORKSPACE_ROOT
        self.LOGS_DIR = self.LOG_ROOT
        self.CAPTURES_DIR = self.CAPTURE_ROOT
        self.ARTIFACTS_DIR = self.ARTIFACT_ROOT
        self.PID_FILE = self.STATE_ROOT / ".jarvis.pid"

        self.ensure_directories()

    def ensure_directories(self) -> None:
        """Ensure all required runtime and workspace directories exist."""
        for d in (
            self.RUNTIME_ROOT,
            self.ARTIFACT_ROOT,
            self.LOG_ROOT,
            self.CAPTURE_ROOT,
            self.REPORT_ROOT,
            self.TEMP_ROOT,
            self.STATE_ROOT,
            self.MEMORY_ROOT,
            self.WORKSPACE_ROOT,
            self.DOCUMENTS_DIR,
            self.RESUMES_DIR,
            self.CAREER_DIR,
            self.PROJECTS_DIR,
            self.USER_DATA_DIR,
        ):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> PathManager:
        if cls._instance is None:
            cls._instance = PathManager()
        return cls._instance


def get_path_manager() -> PathManager:
    return PathManager.get_instance()


paths = get_path_manager()
