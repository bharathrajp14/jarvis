# core/execution/process_runner.py — Centralized Subprocess Lifecycle & Process Tree Runner
from __future__ import annotations

import logging
import os
import platform
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .environment_resolver import get_environment_resolver
from .types import EnvironmentProfile, ExecutionResult, ExecutionStatus

logger = logging.getLogger("JARVIS.ProcessRunner")

_OS = platform.system()
_DEFAULT_TIMEOUT = 30
_MAX_MEMORY_BYTES = 512 * 1024 * 1024  # 512 MB ceiling

_SAFE_ENV_KEYS: Set[str] = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "PYTHONIOENCODING",
    "PYTHONUTF8",
    "PYTHONDONTWRITEBYTECODE",
    "LANG",
    "LC_ALL",
    "TERM",
    "HOMEDRIVE",
    "HOMEPATH",
    "USERPROFILE",
    "VIRTUAL_ENV",
    "PYTHONPATH",
}


class WindowsJobObject:
    """Encapsulates Windows Kernel32 Job Object for guaranteed process tree containment."""

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
                    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
                    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100

                    class IO_COUNTERS(ctypes.Structure):
                        _fields_ = [
                            ("ReadOperationCount", ctypes.c_uint64),
                            ("WriteOperationCount", ctypes.c_uint64),
                            ("OtherOperationCount", ctypes.c_uint64),
                            ("ReadTransferCount", ctypes.c_uint64),
                            ("WriteTransferCount", ctypes.c_uint64),
                            ("OtherTransferCount", ctypes.c_uint64),
                        ]

                    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                        _fields_ = [
                            ("PerProcessUserTimeLimit", ctypes.c_int64),
                            ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", ctypes.wintypes.DWORD),
                            ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t),
                            ("ActiveProcessLimit", ctypes.wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t),
                            ("PriorityClass", ctypes.wintypes.DWORD),
                            ("SchedulingClass", ctypes.wintypes.DWORD),
                        ]

                    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                        _fields_ = [
                            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                            ("IoInfo", IO_COUNTERS),
                            ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryLimit", ctypes.c_size_t),
                            ("PeakJobMemoryLimit", ctypes.c_size_t),
                        ]

                    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
                    info.BasicLimitInformation.LimitFlags = (
                        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_PROCESS_MEMORY
                    )
                    info.ProcessMemoryLimit = max_memory_bytes
                    info.JobMemoryLimit = max_memory_bytes

                    JobObjectExtendedLimitInformation = 9
                    kernel32.SetInformationJobObject(
                        self.handle, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)
                    )
            except Exception as e:
                logger.debug("Windows Job Object setup notice: %s", e)

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


class ProcessRunner:
    """
    Centralized Subprocess Lifecycle & Process Tree Runner.
    Guarantees proper environment propagation, output capture, and zero orphan processes.
    """

    def __init__(self, env_resolver=None):
        self.env_resolver = env_resolver or get_environment_resolver()
        self._active_processes: Dict[int, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def run(
        self,
        command: List[str] | str,
        cwd: Optional[Path | str] = None,
        env_profile: Optional[EnvironmentProfile] = None,
        extra_env: Optional[Dict[str, str]] = None,
        timeout_sec: float = _DEFAULT_TIMEOUT,
        input_text: Optional[str] = None,
        shell: bool = False,
    ) -> ExecutionResult:
        """Execute a command synchronously with full lifecycle management and process tree containment."""
        t0 = time.perf_counter()

        # 1. Resolve runtime environment
        profile = env_profile or self.env_resolver.resolve_python()
        working_dir = (
            Path(cwd).resolve() if cwd else Path(profile.working_directory or self.env_resolver.default_project_root)
        )
        working_dir.mkdir(parents=True, exist_ok=True)

        # 2. Build sanitized environment
        env = self.env_resolver.get_runtime_environment_vars(profile)
        if extra_env:
            for k, v in extra_env.items():
                k_upper = k.upper()
                if not any(s in k_upper for s in ("KEY", "SECRET", "TOKEN", "AUTH", "PASS", "CRED", "SESSION")):
                    env[k] = v

        cmd_str = command if isinstance(command, str) else " ".join(command)
        job = WindowsJobObject(max_memory_bytes=_MAX_MEMORY_BYTES)
        proc = None

        try:
            kwargs: Dict[str, Any] = {
                "cwd": str(working_dir),
                "env": env,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "shell": shell,
            }

            if _OS == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                kwargs["start_new_session"] = True

            proc = subprocess.Popen(command, **kwargs)

            with self._lock:
                self._active_processes[proc.pid] = proc

            # Attach to Windows Job Object for process tree containment
            if _OS == "Windows" and job.handle:
                try:
                    job.assign_process(proc._handle)
                except Exception:
                    pass

            stdout_data, stderr_data = proc.communicate(input=input_text, timeout=max(1.0, timeout_sec))
            duration_ms = (time.perf_counter() - t0) * 1000.0

            status = ExecutionStatus.SUCCESS_UNVERIFIED if proc.returncode == 0 else ExecutionStatus.FAILED

            # Check for silent errors in stderr
            error_msg = None
            if proc.returncode != 0:
                error_msg = stderr_data.strip() or f"Process exited with non-zero returncode: {proc.returncode}"
                if "ModuleNotFoundError" in stderr_data or "ImportError" in stderr_data:
                    status = ExecutionStatus.MISSING_DEPENDENCY
                elif "PermissionError" in stderr_data or "Access is denied" in stderr_data:
                    status = ExecutionStatus.PERMISSION_DENIED
                elif "FileNotFoundError" in stderr_data:
                    status = ExecutionStatus.ENVIRONMENT_ERROR

            return ExecutionResult(
                status=status,
                tool_or_command=cmd_str,
                runtime=profile,
                executable=profile.executable,
                cwd=str(working_dir),
                return_code=proc.returncode,
                stdout=stdout_data,
                stderr=stderr_data,
                output=stdout_data if proc.returncode == 0 else stderr_data,
                evidence=f"Executed '{cmd_str[:60]}' -> returncode {proc.returncode} ({duration_ms:.1f}ms)",
                error=error_msg,
                duration_ms=duration_ms,
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self.kill_process_tree(proc)
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                tool_or_command=cmd_str,
                runtime=profile,
                executable=profile.executable,
                cwd=str(working_dir),
                return_code=-1,
                stderr=f"Execution timed out after {timeout_sec} seconds. Process tree terminated.",
                error=f"Timeout after {timeout_sec}s",
                duration_ms=duration_ms,
            )
        except FileNotFoundError as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ExecutionResult(
                status=ExecutionStatus.ENVIRONMENT_ERROR,
                tool_or_command=cmd_str,
                runtime=profile,
                executable=profile.executable,
                cwd=str(working_dir),
                return_code=-1,
                stderr=str(e),
                error=f"Executable not found on system: {e}",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self.kill_process_tree(proc)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                tool_or_command=cmd_str,
                runtime=profile,
                executable=profile.executable,
                cwd=str(working_dir),
                return_code=-1,
                stderr=str(e),
                error=f"Subprocess execution error: {e}",
                duration_ms=duration_ms,
            )
        finally:
            if proc and proc.pid in self._active_processes:
                with self._lock:
                    self._active_processes.pop(proc.pid, None)
            job.close()

    def kill_process_tree(self, proc: Optional[subprocess.Popen]) -> None:
        """Kill entire process tree cleanly on timeout or cancellation."""
        if not proc or proc.poll() is not None:
            return

        try:
            if _OS == "Windows":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=5)
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception as e:
            logger.debug("Process tree termination notice: %s", e)
            try:
                proc.kill()
            except Exception:
                pass


_GLOBAL_PROCESS_RUNNER: Optional[ProcessRunner] = None


def get_process_runner() -> ProcessRunner:
    global _GLOBAL_PROCESS_RUNNER
    if _GLOBAL_PROCESS_RUNNER is None:
        _GLOBAL_PROCESS_RUNNER = ProcessRunner()
    return _GLOBAL_PROCESS_RUNNER
