"""
BR Voice Assistant — CLI Controller (actions/cli_controller.py)
Windows-specialized terminal command execution. Optimized for PowerShell/CMD.
"""
from __future__ import annotations

import logging
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_OS = platform.system()

# ── Shell detection ───────────────────────────────────────────────────────────

def _detect_shell() -> str:
    """Return the best available shell for the host operating system."""
    if platform.system() == "Windows":
        for sh in ["pwsh.exe", "powershell.exe", "cmd.exe"]:
            if shutil.which(sh):
                return sh
        return "cmd.exe"
    else:
        env_shell = os.environ.get("SHELL", "")
        if env_shell and shutil.which(env_shell):
            return env_shell
        for sh in ["/bin/bash", "/bin/zsh", "/bin/sh"]:
            if shutil.which(sh):
                return sh
        return "/bin/sh"

SHELL     = _detect_shell()
TIMEOUT_S = 30          # default command timeout
MAX_OUT   = 32_000      # max output bytes kept per session


class ShellSession:
    """A persistent, interactive command shell session."""

    def __init__(self, shell: str = SHELL, cwd: str = None):
        self.shell     = shell
        self.cwd       = cwd or str(Path.home())
        self._proc:    Optional[subprocess.Popen]  = None
        self._outbuf   = bytearray()
        self._lock     = threading.Lock()
        self._out_q: queue.Queue[str]              = queue.Queue(maxsize=500)
        self._alive    = False
        self._reader:  Optional[threading.Thread]  = None

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self) -> str:
        if self._alive:
            return "Session already running."
        
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        popen_kwargs = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "cwd": self.cwd,
            "env": env,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            
        self._proc = subprocess.Popen([self.shell], **popen_kwargs)
        self._alive = True
        self._reader = threading.Thread(
            target=self._read_pipe_win, daemon=True,
            name="ShellPipeReader"
        )
        self._reader.start()
        return f"Shell session started ({_OS}): {self.shell}"

    def stop(self) -> str:
        self._alive = False
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception as e:
                    logger.debug('Suppressed exception: %s', e)
        self._proc = None
        return "Shell session stopped."

    # ── Reader thread ──────────────────────────────────────────────────────

    def _read_pipe_win(self):
        if not self._proc or not self._proc.stdout:
            return
        for line in self._proc.stdout:
            if not self._alive:
                break
            with self._lock:
                self._outbuf.extend(line.encode("utf-8", errors="replace"))
                if len(self._outbuf) > MAX_OUT:
                    self._outbuf = self._outbuf[-MAX_OUT:]
            try:
                self._out_q.put_nowait(line)
            except queue.Full:
                pass

    # ── Command execution ──────────────────────────────────────────────────

    def run_cmd(self, cmd: str, timeout: float = TIMEOUT_S) -> str:
        """Send a command to the shell and return its output."""
        if not self._alive:
            self.start()

        # Sentinel to detect command completion
        sentinel = f"__BR_DONE_{int(time.time() * 1000)}__"
        full_cmd = f"{cmd}\r\necho {sentinel}\r\n"
        
        try:
            self._proc.stdin.write(full_cmd)
            self._proc.stdin.flush()
        except Exception as e:
            return f"Command send error: {e}"

        # Collect output until sentinel or timeout
        collected = []
        deadline  = time.time() + timeout
        found_sent = False

        while time.time() < deadline and not found_sent:
            try:
                chunk = self._out_q.get(timeout=0.15)
                if sentinel in chunk:
                    part = chunk[:chunk.index(sentinel)]
                    if part:
                        collected.append(part)
                    found_sent = True
                else:
                    collected.append(chunk)
            except queue.Empty:
                if self._proc and self._proc.poll() is not None:
                    break

        output = "".join(collected)
        lines = output.splitlines()
        if lines and cmd.strip() in lines[0]:
            lines = lines[1:]
        output = "\n".join(lines).strip()
        return output or "(no output)"

    def _drain(self, secs: float):
        """Drain pending output for a short time."""
        deadline = time.time() + secs
        while time.time() < deadline:
            try:
                self._out_q.get_nowait()
            except queue.Empty:
                break

    def get_cwd(self) -> str:
        """Get current working directory of Windows shell."""
        result = self.run_cmd("cd", timeout=5)
        for line in result.splitlines():
            line = line.strip()
            if line and len(line) > 2 and line[1] == ":":
                return line
        return self.cwd

    def send_input(self, text: str) -> str:
        """Send raw input to an interactive program."""
        if not self._alive:
            return "Session not running."
        if self._proc and self._proc.stdin:
            self._proc.stdin.write(text + "\n")
            self._proc.stdin.flush()
        return f"Sent: {text[:80]}"

    @property
    def alive(self) -> bool:
        if not self._alive:
            return False
        if self._proc and self._proc.poll() is not None:
            self._alive = False
        return self._alive


# ── Session registry ──────────────────────────────────────────────────────────

_sessions:  dict[str, ShellSession] = {}
_main_sess: Optional[ShellSession]  = None
_sess_lock  = threading.Lock()


def _get_main_session() -> ShellSession:
    global _main_sess
    with _sess_lock:
        if _main_sess is None or not _main_sess.alive:
            _main_sess = ShellSession()
            _main_sess.start()
        return _main_sess


def _get_named_session(name: str) -> ShellSession:
    with _sess_lock:
        if name not in _sessions or not _sessions[name].alive:
            sess = ShellSession()
            sess.start()
            _sessions[name] = sess
        return _sessions[name]


# ── Subprocess (one-shot) ──────────────────────────────────────────────────────

def _run_oneshot(
    cmd: str,
    cwd: str = None,
    timeout: int = TIMEOUT_S,
    env_extra: dict = None,
) -> dict:
    """Execute a command in a fresh Windows subprocess and capture output."""
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    env["PYTHONUNBUFFERED"] = "1"

    if platform.system() == "Windows":
        exec_cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd]
    else:
        shell_bin = shutil.which("bash") or "/bin/sh"
        exec_cmd = [shell_bin, "-lc", cmd]

    try:
        result = subprocess.run(
            exec_cmd,
            shell=False,
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            cwd=cwd or str(Path.home()),
            env=env, timeout=timeout,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        return {
            "stdout":     stdout,
            "stderr":     stderr,
            "returncode": result.returncode,
            "success":    result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timed out after {timeout}s.",
                "returncode": -1, "success": False}
    except FileNotFoundError as e:
        return {"stdout": "", "stderr": f"Command not found: {e}",
                "returncode": -1, "success": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e),
                "returncode": -1, "success": False}


def _fmt_result(r: dict) -> str:
    parts = []
    if r.get("stdout"):
        parts.append(r["stdout"])
    if r.get("stderr"):
        parts.append(f"[stderr]\n{r['stderr']}")
    if not parts:
        parts.append("(no output)")
    rc = r.get("returncode", 0)
    if rc != 0:
        parts.append(f"[exit code: {rc}]")
    return "\n".join(parts)


# ── Main entry point ──────────────────────────────────────────────────────────

def cli_controller(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params  = parameters or {}
    action  = params.get("action", "run").lower().strip()
    cmd     = params.get("cmd",     "").strip()
    name    = params.get("name",    "main").strip()
    cwd     = params.get("cwd",     "").strip() or None
    timeout = int(params.get("timeout", TIMEOUT_S))

    if player:
        player.write_log(f"[CLI] {action}: {cmd[:60]}")

    logger.info(f"[CLIController] ▶ {action}  '{cmd[:60]}'")

    # ── Actions ───────────────────────────────────────────────────────────

    if action == "run":
        if not cmd:
            return "No command specified."
        r = _run_oneshot(cmd, cwd=cwd, timeout=timeout)
        return _fmt_result(r)

    if action == "run_session":
        if not cmd:
            return "No command specified."
        sess = _get_named_session(name) if name != "main" else _get_main_session()
        return sess.run_cmd(cmd, timeout=timeout)

    if action == "send_input":
        sess = _get_named_session(name) if name != "main" else _get_main_session()
        return sess.send_input(cmd or params.get("text", ""))

    if action == "cd":
        if not cmd:
            return "No directory specified."
        target = cmd.strip()
        sess   = _get_main_session()
        result = sess.run_cmd(f"cd \"{target}\" && cd", timeout=8)
        return result

    if action == "pwd":
        sess = _get_main_session()
        return sess.get_cwd()

    if action == "python":
        code = cmd or params.get("code", "")
        if not code:
            return "No Python code specified."
        
        # On Windows wrap code safely for python -c
        safe_code = code.replace('"', '\\"')
        r = _run_oneshot(
            f'"{sys.executable}" -c "{safe_code}"',
            cwd=cwd, timeout=timeout
        )
        return _fmt_result(r)

    if action == "pipe":
        if not cmd:
            return "No pipe command specified."
        r = _run_oneshot(cmd, cwd=cwd, timeout=timeout)
        return _fmt_result(r)

    if action == "bg":
        if not cmd:
            return "No command specified."
        try:
            popen_kwargs = {
                "shell": True,
                "cwd": cwd or str(Path.home()),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            p = subprocess.Popen(cmd, **popen_kwargs)
            return f"Background process started. PID: {p.pid}. Command: {cmd[:60]}"
        except Exception as e:
            return f"Background start error: {e}"

    if action == "which":
        target = cmd or params.get("target", "")
        if not target:
            return "No command to look up."
        path = shutil.which(target)
        return path if path else f"'{target}' not found in PATH"

    if action == "env":
        key   = params.get("key",   "").strip()
        value = params.get("value", "").strip()
        if key and value:
            os.environ[key] = value
            return f"Set {key}={value}"
        if key:
            return os.environ.get(key, f"(not set: {key})")
        lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
        return "\n".join(lines[:40]) + (f"\n... ({len(lines)} total)" if len(lines) > 40 else "")

    if action == "session_new":
        with _sess_lock:
            sess = ShellSession(cwd=cwd)
            msg  = sess.start()
            _sessions[name] = sess
        return f"Session '{name}' created. {msg}"

    if action == "session_end":
        with _sess_lock:
            sess = _sessions.pop(name, None)
        if sess:
            return sess.stop()
        return f"No session named '{name}'."

    if action == "history":
        return "Command history is not supported on session."

    if action == "auto" or action == "":
        return _auto_dispatch(cmd, cwd, timeout)

    return f"Unknown CLI action: '{action}'."


def _auto_dispatch(cmd: str, cwd: str, timeout: int) -> str:
    if not cmd:
        return "No command provided."

    low = cmd.lower().strip()

    if _OS == "Windows":
        mappings = {
            "list files":        "dir",
            "show directory":    "cd",
            "current directory": "cd",
            "show processes":    "tasklist",
            "disk usage":        "wmic logicaldisk get size,freespace,caption",
            "network interfaces":"ipconfig",
            "memory usage":      "systeminfo | findstr Memory",
            "cpu info":          "wmic cpu get Name",
            "show path":         "echo %PATH%",
            "clear screen":      "cls",
            "running services":  "Get-Service | Where Status -eq Running",
        }
    else:
        mappings = {
            "list files":        "ls -la",
            "show directory":    "pwd",
            "current directory": "pwd",
            "show processes":    "ps aux",
            "disk usage":        "df -h",
            "network interfaces":"ip a || ifconfig",
            "memory usage":      "free -h",
            "cpu info":          "lscpu || uname -a",
            "show path":         "echo $PATH",
            "clear screen":      "clear",
            "running services":  "systemctl list-units --type=service --state=running || ps aux",
        }

    for phrase, shell_cmd in mappings.items():
        if phrase in low:
            r = _run_oneshot(shell_cmd, cwd=cwd, timeout=timeout)
            return f"[{shell_cmd}]\n{_fmt_result(r)}"

    r = _run_oneshot(cmd, cwd=cwd, timeout=timeout)
    return _fmt_result(r)
