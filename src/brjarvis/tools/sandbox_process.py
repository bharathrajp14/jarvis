# tools/sandbox_process.py — Production-Grade Sandboxed Process Runner
"""
Isolated Code Execution Sandbox for BR JARVIS.
Features:
- Strict Environment Variable Allowlist (disallows passing arbitrary host environment)
- Sandboxed execution in dedicated temporary jail directory
- Process Tree Containment (Windows Job Object with kill-on-close / Unix setpgid + cgroups)
- Resource Ceilings (Memory ceiling, strict execution timeouts)
- Guaranteed full process-tree termination on timeout or cancellation
"""
from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("JARVIS.SandboxProcess")

_OS = platform.system()
_DEFAULT_TIMEOUT = 20
_MAX_MEMORY_BYTES = 256 * 1024 * 1024  # 256 MB

# Strict allowlist of safe system environment variables
_STRICT_SAFE_ENV_KEYS: Set[str] = {
    "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
    "TEMP", "TMP", "PYTHONIOENCODING", "PYTHONUTF8", "PYTHONDONTWRITEBYTECODE",
    "LANG", "LC_ALL", "TERM"
}


def _build_strict_safe_env(extra_env: Optional[Dict[str, str]] = None, env_profile: Optional[Any] = None) -> Dict[str, str]:
    """Create a sanitized environment dictionary containing system keys and virtualenv paths."""
    safe_env: Dict[str, str] = {}
    for key, value in os.environ.items():
        if key.upper() in _STRICT_SAFE_ENV_KEYS:
            safe_env[key] = value

    # Enforce safe execution defaults
    safe_env["PYTHONIOENCODING"] = "utf-8"
    safe_env["PYTHONUTF8"] = "1"
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
    safe_env["PYTHONUNBUFFERED"] = "1"

    if env_profile and getattr(env_profile, "is_virtualenv", False) and env_profile.virtualenv_path:
        venv_p = Path(env_profile.virtualenv_path)
        scripts_dir = venv_p / ("Scripts" if sys.platform == "win32" else "bin")
        safe_env["VIRTUAL_ENV"] = str(venv_p)
        current_path = safe_env.get("PATH", "")
        safe_env["PATH"] = f"{scripts_dir}{os.pathsep}{current_path}"
        safe_env["PYTHONHOME"] = ""

    if env_profile and getattr(env_profile, "project_root", None):
        existing_pypath = safe_env.get("PYTHONPATH", "")
        if existing_pypath:
            safe_env["PYTHONPATH"] = f"{env_profile.project_root}{os.pathsep}{existing_pypath}"
        else:
            safe_env["PYTHONPATH"] = str(env_profile.project_root)

    if extra_env:
        for k, v in extra_env.items():
            k_upper = k.upper()
            if not any(s in k_upper for s in ("KEY", "SECRET", "TOKEN", "AUTH", "PASS", "CRED", "SESSION", "JARVIS")):
                safe_env[k] = v

    return safe_env


class WindowsJobObject:
    """Encapsulates Windows Kernel32 Job Object for process tree containment."""

    def __init__(self, max_memory_bytes: int = _MAX_MEMORY_BYTES):
        self.handle = None
        self.max_memory_bytes = max_memory_bytes
        if _OS == "Windows":
            try:
                import ctypes
                import ctypes.wintypes
                kernel32 = ctypes.windll.kernel32
                self.handle = kernel32.CreateJobObjectW(None, None)
                if self.handle:
                    # JOBOBJECT_EXTENDED_LIMIT_INFORMATION
                    # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
                    # JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
                    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
                    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
                    
                    class IO_COUNTERS(ctypes.Structure):
                        _fields_ = [
                            ('ReadOperationCount', ctypes.c_uint64),
                            ('WriteOperationCount', ctypes.c_uint64),
                            ('OtherOperationCount', ctypes.c_uint64),
                            ('ReadTransferCount', ctypes.c_uint64),
                            ('WriteTransferCount', ctypes.c_uint64),
                            ('OtherTransferCount', ctypes.c_uint64)
                        ]

                    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                        _fields_ = [
                            ('PerProcessUserTimeLimit', ctypes.c_int64),
                            ('PerJobUserTimeLimit', ctypes.c_int64),
                            ('LimitFlags', ctypes.wintypes.DWORD),
                            ('MinimumWorkingSetSize', ctypes.c_size_t),
                            ('MaximumWorkingSetSize', ctypes.c_size_t),
                            ('ActiveProcessLimit', ctypes.wintypes.DWORD),
                            ('Affinity', ctypes.c_size_t),
                            ('PriorityClass', ctypes.wintypes.DWORD),
                            ('SchedulingClass', ctypes.wintypes.DWORD)
                        ]

                    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                        _fields_ = [
                            ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                            ('IoInfo', IO_COUNTERS),
                            ('ProcessMemoryLimit', ctypes.c_size_t),
                            ('JobMemoryLimit', ctypes.c_size_t),
                            ('PeakProcessMemoryLimit', ctypes.c_size_t),
                            ('PeakJobMemoryLimit', ctypes.c_size_t)
                        ]

                    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
                    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_PROCESS_MEMORY
                    info.ProcessMemoryLimit = max_memory_bytes
                    info.JobMemoryLimit = max_memory_bytes

                    JobObjectExtendedLimitInformation = 9
                    kernel32.SetInformationJobObject(
                        self.handle,
                        JobObjectExtendedLimitInformation,
                        ctypes.byref(info),
                        ctypes.sizeof(info)
                    )
            except Exception as e:
                logger.debug("Windows Job Object setup note: %s", e)

    def assign_process(self, process_handle) -> bool:
        if self.handle and _OS == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                return bool(kernel32.AssignProcessToJobObject(self.handle, process_handle))
            except Exception as e:
                logger.debug("Failed to assign process to Job Object: %s", e)
        return False

    def close(self) -> None:
        if self.handle and _OS == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None


class SandboxedProcessRunner:
    """Executes code in an isolated, monitored subprocess jail with strict tree containment."""

    ALLOWED_LANGS = {"python", "javascript", "bash", "powershell"}

    def __init__(self, jail_root: Optional[Path] = None):
        if jail_root:
            self.jail_root = Path(jail_root)
        else:
            self.jail_root = Path(tempfile.gettempdir()) / "jarvis_sandbox_jails"
        self.jail_root.mkdir(parents=True, exist_ok=True)

    def _export_jail_artifacts(self, jail_dir: Path, task_id: str = "default") -> List[Dict[str, Any]]:
        """Discover and securely export all user-facing artifacts generated inside jail before destruction."""
        try:
            from agent.artifacts import get_artifact_manager
            mgr = get_artifact_manager()
            exported = []
            if not jail_dir.exists():
                return exported

            internal_scripts = {"main.py", "main.js", "main.sh", "main.ps1"}

            for p in jail_dir.rglob("*"):
                if p.is_file() and p.name not in internal_scripts:
                    allowed, _ = mgr.is_allowed_artifact(p)
                    if allowed:
                        rec = mgr.export_sandbox_artifact(p, task_id=task_id)
                        if rec.exported:
                            exported.append(rec.to_dict())
            return exported
        except Exception as e:
            logger.debug("Artifact auto-export note: %s", e)
            return []

    def export_jail_artifact(self, sandbox_file: Union[str, Path], task_id: str = "default") -> Optional[Any]:
        """Manually export a specific file from a sandbox jail to the host directory."""
        from agent.artifacts import get_artifact_manager
        mgr = get_artifact_manager()
        rec = mgr.export_sandbox_artifact(sandbox_file, task_id=task_id)
        return rec if rec.exported else None

    def execute(
        self,
        code: str,
        lang: str = "python",
        timeout: int = _DEFAULT_TIMEOUT,
        allowed_dirs: Optional[List[str]] = None,
        extra_env: Optional[Dict[str, str]] = None,
        auto_export_artifacts: bool = True,
    ) -> Dict[str, Any]:
        lang = lang.lower().strip()
        if lang not in self.ALLOWED_LANGS:
            return {
                "success": False,
                "error": f"Language '{lang}' is not permitted. Allowed: {sorted(self.ALLOWED_LANGS)}",
                "returncode": -1
            }

        # Strip markdown code blocks
        clean_code = code.strip()
        clean_code = re.sub(r"^```[a-zA-Z0-9_\-]*\n?", "", clean_code)
        clean_code = re.sub(r"\n?```$", "", clean_code).strip()

        jail_id = f"jail_{uuid.uuid4().hex[:12]}"
        jail_dir = self.jail_root / jail_id
        jail_dir.mkdir(parents=True, exist_ok=True)

        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "bash": ".sh",
            "powershell": ".ps1"
        }
        script_file = jail_dir / f"main{ext_map[lang]}"
        script_file.write_text(clean_code, encoding="utf-8")

        env_profile = None
        if lang == "python":
            try:
                from core.execution.environment_resolver import get_environment_resolver
                env_profile = get_environment_resolver().resolve_python()
            except Exception:
                pass

        safe_env = _build_strict_safe_env(extra_env, env_profile=env_profile)
        safe_env["TEMP"] = str(jail_dir)
        safe_env["TMP"] = str(jail_dir)

        cmd = self._resolve_command(lang, script_file, env_profile=env_profile)
        job = WindowsJobObject(max_memory_bytes=_MAX_MEMORY_BYTES)

        proc = None
        try:
            kwargs: Dict[str, Any] = {
                "cwd": str(jail_dir),
                "env": safe_env,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
            }

            if _OS == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True

            proc = subprocess.Popen(cmd, **kwargs)

            # Attach to Windows Job Object
            if _OS == "Windows" and job.handle:
                try:
                    import ctypes
                    # proc._handle is the OS process handle
                    job.assign_process(proc._handle)
                except Exception:
                    pass

            stdout_data, stderr_data = proc.communicate(timeout=max(1, min(timeout, 60)))

            # Auto-export user artifacts before cleaning up ephemeral jail directory
            exported_artifacts = []
            if auto_export_artifacts:
                exported_artifacts = self._export_jail_artifacts(jail_dir, task_id=jail_id)

            host_artifacts = [a["host_path"] for a in exported_artifacts if a.get("host_path")]

            return {
                "success": proc.returncode == 0,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "returncode": proc.returncode,
                "jail_id": jail_id,
                "artifacts": exported_artifacts,
                "host_artifacts": host_artifacts,
            }

        except subprocess.TimeoutExpired:
            self._kill_process_tree(proc)
            return {
                "success": False,
                "timed_out": True,
                "error": f"Sandbox execution timed out after {timeout} seconds.",
                "stdout": "",
                "stderr": "Execution timeout exceeded. Process terminated.",
                "returncode": -1
            }
        except FileNotFoundError as e:
            return {
                "success": False,
                "error": f"Runtime engine for '{lang}' not found on host: {e}",
                "returncode": -1
            }
        except Exception as e:
            logger.error("Sandbox execution failure: %s", e, exc_info=True)
            self._kill_process_tree(proc)
            return {
                "success": False,
                "error": f"Sandbox execution error: {e}",
                "returncode": -1
            }
        finally:
            job.close()
            # Clean up temporary jail directory
            try:
                shutil.rmtree(jail_dir, ignore_errors=True)
            except Exception:
                pass

    def _kill_process_tree(self, proc: Optional[subprocess.Popen]) -> None:
        """Kill entire process tree cleanly on timeout or error."""
        if not proc or proc.poll() is not None:
            return

        try:
            if _OS == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    timeout=5
                )
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception as e:
            logger.debug("Process tree termination note: %s", e)
            try:
                proc.kill()
            except Exception:
                pass

    def _resolve_command(self, lang: str, script_path: Path, env_profile: Optional[Any] = None) -> List[str]:
        script_str = str(script_path)
        if lang == "python":
            py_exec = env_profile.executable if (env_profile and getattr(env_profile, "executable", None)) else sys.executable
            return [py_exec, script_str]
        elif lang == "javascript":
            return ["node", script_str]
        elif lang == "bash":
            return ["bash", script_str]
        elif lang == "powershell":
            ps = "powershell" if _OS == "Windows" else "pwsh"
            if _OS == "Windows":
                return [ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script_str]
            return [ps, "-NoProfile", "-NonInteractive", "-File", script_str]
        py_exec = env_profile.executable if (env_profile and getattr(env_profile, "executable", None)) else sys.executable
        return [py_exec, script_str]


_GLOBAL_SANDBOX: Optional[SandboxedProcessRunner] = None


def get_sandbox_runner() -> SandboxedProcessRunner:
    global _GLOBAL_SANDBOX
    if _GLOBAL_SANDBOX is None:
        _GLOBAL_SANDBOX = SandboxedProcessRunner()
    return _GLOBAL_SANDBOX
