# core/execution/environment_resolver.py — Deterministic 6-Tier Environment Resolver
from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .types import EnvironmentProfile, RuntimeType

logger = logging.getLogger("JARVIS.EnvironmentResolver")


class EnvironmentResolver:
    """
    Deterministic 6-Tier Environment Resolution Engine for BR JARVIS.
    
    Precedence Policy:
      Tier 1: Explicit task / runtime configuration
      Tier 2: Project-local environment (.venv / node_modules)
      Tier 3: Repository-local executable / scripts
      Tier 4: User-configured environment (.env / JARVIS_PYTHON_PATH)
      Tier 5: System environment (PATH lookup)
      Tier 6: Global fallback (with recorded warning)
    """

    _INSTANCE: Optional[EnvironmentResolver] = None

    def __init__(self, default_project_root: Optional[Path | str] = None):
        if default_project_root:
            self.default_project_root = Path(default_project_root).resolve()
        else:
            self.default_project_root = Path(__file__).resolve().parent.parent.parent
        self._cache: Dict[str, EnvironmentProfile] = {}

    @classmethod
    def get_instance(cls, default_project_root: Optional[Path | str] = None) -> EnvironmentResolver:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls(default_project_root)
        return cls._INSTANCE

    def resolve_python(
        self,
        project_root: Optional[Path | str] = None,
        explicit_path: Optional[str] = None,
        working_dir: Optional[Path | str] = None,
    ) -> EnvironmentProfile:
        """Resolve the Python environment adhering strictly to the 6-tier precedence policy."""
        root = Path(project_root).resolve() if project_root else self.default_project_root
        cwd = Path(working_dir).resolve() if working_dir else root

        cache_key = f"python:{root}:{explicit_path or ''}"
        if cache_key in self._cache:
            profile = self._cache[cache_key]
            # update working dir if needed
            profile.working_directory = str(cwd)
            return profile

        # Tier 1: Explicit task / runtime configuration
        if explicit_path:
            p = Path(explicit_path).resolve()
            if p.exists() and p.is_file():
                ver = self._inspect_python_version(str(p))
                profile = EnvironmentProfile(
                    runtime_type=RuntimeType.PYTHON,
                    executable=str(p),
                    version=ver,
                    is_virtualenv=self._is_virtualenv(p),
                    virtualenv_path=str(p.parent.parent) if self._is_virtualenv(p) else None,
                    project_root=str(root),
                    working_directory=str(cwd),
                    precedence_tier=1,
                    precedence_source="explicit_configuration",
                    notes="Explicitly specified Python executable",
                )
                self._cache[cache_key] = profile
                return profile

        # Tier 2: Project-local virtual environment (.venv, venv, env)
        venv_candidates = [
            root / ".venv",
            root / "venv",
            root / "env",
            root / ".env_py",
        ]
        for venv_dir in venv_candidates:
            if venv_dir.exists() and venv_dir.is_dir():
                py_exec = self._get_venv_python_executable(venv_dir)
                if py_exec and py_exec.exists():
                    ver = self._inspect_python_version(str(py_exec))
                    profile = EnvironmentProfile(
                        runtime_type=RuntimeType.PYTHON,
                        executable=str(py_exec),
                        version=ver,
                        is_virtualenv=True,
                        virtualenv_path=str(venv_dir),
                        project_root=str(root),
                        working_directory=str(cwd),
                        precedence_tier=2,
                        precedence_source="project_virtualenv",
                        notes=f"Project virtualenv located at {venv_dir}",
                    )
                    self._cache[cache_key] = profile
                    return profile

        # Tier 3: Repository-local executable / scripts
        repo_bin_candidates = [
            root / "bin" / ("python.exe" if sys.platform == "win32" else "python"),
            root / "Scripts" / "python.exe",
        ]
        for bin_exec in repo_bin_candidates:
            if bin_exec.exists() and bin_exec.is_file():
                ver = self._inspect_python_version(str(bin_exec))
                profile = EnvironmentProfile(
                    runtime_type=RuntimeType.PYTHON,
                    executable=str(bin_exec),
                    version=ver,
                    is_virtualenv=False,
                    project_root=str(root),
                    working_directory=str(cwd),
                    precedence_tier=3,
                    precedence_source="repo_local_executable",
                    notes="Repository-local binary directory",
                )
                self._cache[cache_key] = profile
                return profile

        # Tier 4: User-configured environment in .env or os.environ
        env_configured = os.environ.get("JARVIS_PYTHON_PATH") or os.environ.get("PYTHON_PATH")
        if env_configured:
            p = Path(env_configured).resolve()
            if p.exists() and p.is_file():
                ver = self._inspect_python_version(str(p))
                profile = EnvironmentProfile(
                    runtime_type=RuntimeType.PYTHON,
                    executable=str(p),
                    version=ver,
                    is_virtualenv=self._is_virtualenv(p),
                    virtualenv_path=str(p.parent.parent) if self._is_virtualenv(p) else None,
                    project_root=str(root),
                    working_directory=str(cwd),
                    precedence_tier=4,
                    precedence_source="user_env_configuration",
                    notes=f"Configured via environment variable JARVIS_PYTHON_PATH={env_configured}",
                )
                self._cache[cache_key] = profile
                return profile

        # Tier 5: System environment (PATH lookup, avoiding Windows Store stub if better exists)
        sys_py = self._find_best_system_python()
        if sys_py:
            ver = self._inspect_python_version(sys_py)
            profile = EnvironmentProfile(
                runtime_type=RuntimeType.PYTHON,
                executable=sys_py,
                version=ver,
                is_virtualenv=self._is_virtualenv(Path(sys_py)),
                project_root=str(root),
                working_directory=str(cwd),
                precedence_tier=5,
                precedence_source="system_path",
                notes="Resolved from system PATH",
            )
            self._cache[cache_key] = profile
            return profile

        # Tier 6: Global fallback (sys.executable)
        current_py = sys.executable
        ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        profile = EnvironmentProfile(
            runtime_type=RuntimeType.PYTHON,
            executable=current_py,
            version=ver,
            is_virtualenv=self._is_virtualenv(Path(current_py)),
            project_root=str(root),
            working_directory=str(cwd),
            precedence_tier=6,
            precedence_source="global_fallback",
            notes="WARNING: Falling back to running host process sys.executable",
        )
        self._cache[cache_key] = profile
        return profile

    def resolve_node(self, project_root: Optional[Path | str] = None) -> EnvironmentProfile:
        """Resolve Node.js executable."""
        root = Path(project_root).resolve() if project_root else self.default_project_root
        
        # Check project node_modules/.bin first
        local_node = root / "node_modules" / ".bin" / ("node.cmd" if sys.platform == "win32" else "node")
        if local_node.exists():
            return EnvironmentProfile(
                runtime_type=RuntimeType.NODE,
                executable=str(local_node),
                project_root=str(root),
                precedence_tier=2,
                precedence_source="project_node_modules",
            )

        # System path
        system_node = shutil.which("node")
        if system_node:
            ver = self._run_version_command([system_node, "--version"])
            return EnvironmentProfile(
                runtime_type=RuntimeType.NODE,
                executable=system_node,
                version=ver,
                project_root=str(root),
                precedence_tier=5,
                precedence_source="system_path",
            )

        return EnvironmentProfile(
            runtime_type=RuntimeType.NODE,
            executable="node",
            is_healthy=False,
            precedence_tier=6,
            precedence_source="not_found",
            notes="Node.js executable was not found on system PATH",
        )

    def resolve_git(self, project_root: Optional[Path | str] = None) -> EnvironmentProfile:
        """Resolve Git executable."""
        root = Path(project_root).resolve() if project_root else self.default_project_root
        git_path = shutil.which("git")
        if git_path:
            ver = self._run_version_command([git_path, "--version"])
            return EnvironmentProfile(
                runtime_type=RuntimeType.GIT,
                executable=git_path,
                version=ver,
                project_root=str(root),
                precedence_tier=5,
                precedence_source="system_path",
            )
        return EnvironmentProfile(
            runtime_type=RuntimeType.GIT,
            executable="git",
            is_healthy=False,
            precedence_tier=6,
            precedence_source="not_found",
            notes="Git executable was not found on system PATH",
        )

    def resolve_powershell(self) -> EnvironmentProfile:
        """Resolve PowerShell (pwsh core or Windows PowerShell)."""
        pwsh = shutil.which("pwsh")
        if pwsh:
            ver = self._run_version_command([pwsh, "--version"])
            return EnvironmentProfile(
                runtime_type=RuntimeType.POWERSHELL,
                executable=pwsh,
                version=ver,
                precedence_tier=5,
                precedence_source="system_pwsh_core",
            )
        win_ps = shutil.which("powershell")
        if win_ps:
            return EnvironmentProfile(
                runtime_type=RuntimeType.POWERSHELL,
                executable=win_ps,
                version="5.1+",
                precedence_tier=5,
                precedence_source="system_windows_powershell",
            )
        return EnvironmentProfile(
            runtime_type=RuntimeType.POWERSHELL,
            executable="powershell",
            is_healthy=False,
            precedence_tier=6,
            precedence_source="not_found",
        )

    def resolve_browser(self) -> EnvironmentProfile:
        """Resolve Playwright Chromium browser executable path."""
        py_prof = self.resolve_python()
        
        # Check standard Playwright cache directory
        user_home = Path.home()
        if sys.platform == "win32":
            cache_dir = user_home / "AppData" / "Local" / "ms-playwright"
        elif sys.platform == "darwin":
            cache_dir = user_home / "Library" / "Caches" / "ms-playwright"
        else:
            cache_dir = user_home / ".cache" / "ms-playwright"

        chromium_exec = None
        if cache_dir.exists():
            for p in cache_dir.glob("chromium-*/chrome-win/chrome.exe"):
                if p.exists():
                    chromium_exec = p
                    break
            if not chromium_exec:
                for p in cache_dir.glob("chromium-*/chrome-linux/chrome"):
                    if p.exists():
                        chromium_exec = p
                        break
            if not chromium_exec:
                for p in cache_dir.glob("chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
                    if p.exists():
                        chromium_exec = p
                        break

        # Check system Chrome or Edge
        if not chromium_exec and sys.platform == "win32":
            chrome_sys = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
            edge_sys = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
            if chrome_sys.exists():
                chromium_exec = chrome_sys
            elif edge_sys.exists():
                chromium_exec = edge_sys

        if chromium_exec and chromium_exec.exists():
            return EnvironmentProfile(
                runtime_type=RuntimeType.BROWSER,
                executable=str(chromium_exec),
                version="Chromium/Chrome",
                is_healthy=True,
                precedence_tier=5,
                precedence_source="playwright_or_system_browser",
            )

        return EnvironmentProfile(
            runtime_type=RuntimeType.BROWSER,
            executable="",
            is_healthy=False,
            precedence_tier=6,
            precedence_source="not_found",
            notes="Playwright Chromium binary not installed. Requires: playwright install chromium",
        )

    def get_runtime_environment_vars(self, profile: EnvironmentProfile) -> Dict[str, str]:
        """Build a clean sanitized environment dict tailored to the resolved runtime."""
        env: Dict[str, str] = {}
        
        # Preserve safe system essentials
        safe_keys = {
            "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
            "TEMP", "TMP", "LANG", "LC_ALL", "TERM", "HOMEDRIVE", "HOMEPATH", "USERPROFILE"
        }
        for k, v in os.environ.items():
            if k.upper() in safe_keys:
                env[k] = v

        if profile.runtime_type == RuntimeType.PYTHON:
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONUNBUFFERED"] = "1"

            if profile.is_virtualenv and profile.virtualenv_path:
                venv_p = Path(profile.virtualenv_path)
                scripts_dir = venv_p / ("Scripts" if sys.platform == "win32" else "bin")
                env["VIRTUAL_ENV"] = str(venv_p)
                # Prepend virtualenv scripts to PATH
                current_path = env.get("PATH", "")
                env["PATH"] = f"{scripts_dir}{os.pathsep}{current_path}"
                env["PYTHONHOME"] = ""  # Unset PYTHONHOME to prevent venv collision

            if profile.project_root:
                # Add project root to PYTHONPATH so local modules can import
                existing_pypath = os.environ.get("PYTHONPATH", "")
                if existing_pypath:
                    env["PYTHONPATH"] = f"{profile.project_root}{os.pathsep}{existing_pypath}"
                else:
                    env["PYTHONPATH"] = profile.project_root

        return env

    # ── Internal Helpers ───────────────────────────────────────────────────

    def _get_venv_python_executable(self, venv_dir: Path) -> Optional[Path]:
        if sys.platform == "win32":
            exec_path = venv_dir / "Scripts" / "python.exe"
        else:
            exec_path = venv_dir / "bin" / "python"
        return exec_path if exec_path.exists() else None

    def _is_virtualenv(self, py_path: Path) -> bool:
        """Detect whether a python executable resides in a virtual environment."""
        parent_dir = py_path.parent
        grandparent_dir = parent_dir.parent
        return (
            (grandparent_dir / "pyvenv.cfg").exists()
            or (parent_dir / "pyvenv.cfg").exists()
            or "venv" in str(py_path).lower()
        )

    def _find_best_system_python(self) -> Optional[str]:
        """Find best system Python executable, skipping Windows Store 0-byte execution aliases."""
        candidates: List[str] = []
        
        # py launcher if available
        py_launcher = shutil.which("py")
        if py_launcher:
            try:
                res = subprocess.run([py_launcher, "-3.12", "-c", "import sys; print(sys.executable)"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0 and res.stdout.strip():
                    candidates.append(res.stdout.strip())
            except Exception:
                pass

        python_which = shutil.which("python")
        if python_which:
            # Check if Windows Store alias
            if "WindowsApps" not in python_which:
                candidates.append(python_which)

        python3_which = shutil.which("python3")
        if python3_which and "WindowsApps" not in python3_which:
            candidates.append(python3_which)

        # Standard installation directories on Windows
        if sys.platform == "win32":
            for ver in ("312", "311", "313", "310"):
                p = Path(f"C:/Python{ver}/python.exe")
                if p.exists():
                    candidates.append(str(p))

        for c in candidates:
            if Path(c).exists() and Path(c).is_file():
                return c

        return python_which or (candidates[0] if candidates else None)

    def _inspect_python_version(self, exec_path: str) -> str:
        try:
            res = subprocess.run([exec_path, "--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                out = (res.stdout or res.stderr).strip()
                return out.replace("Python ", "")
        except Exception:
            pass
        return "unknown"

    def _run_version_command(self, cmd: List[str]) -> str:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                return (res.stdout or res.stderr).strip().splitlines()[0]
        except Exception:
            pass
        return "unknown"


_GLOBAL_RESOLVER: Optional[EnvironmentResolver] = None


def get_environment_resolver(default_project_root: Optional[Path | str] = None) -> EnvironmentResolver:
    global _GLOBAL_RESOLVER
    if _GLOBAL_RESOLVER is None or default_project_root is not None:
        _GLOBAL_RESOLVER = EnvironmentResolver.get_instance(default_project_root)
    return _GLOBAL_RESOLVER
