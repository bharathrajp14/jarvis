# tools/process_tools.py — BR JARVIS System Diagnostics & Process Control Engine
"""
System Diagnostics, Process Manager, and Telemetry Inspection Suite.
"""

from __future__ import annotations

import subprocess
import sys

from .registry import register_tool

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@register_tool(
    name="get_system_diagnostics",
    description="Retrieve real-time system performance telemetry: CPU, RAM, Top 10 memory-hogging processes, disk usage, and active tasks.",
    parameters={
        "type": "object",
        "properties": {
            "top_n": {
                "type": "integer",
                "description": "Number of top memory-consuming processes to report (default: 10)",
            }
        },
    },
)
def get_system_diagnostics(args: dict) -> str:
    """Retrieve system process telemetry."""
    top_n = args.get("top_n", 10)

    if _PSUTIL_AVAILABLE:
        cpu_pct = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        top_procs = []
        for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
            try:
                info = proc.info
                mem_mb = round(info["memory_info"].rss / (1024 * 1024), 1)
                top_procs.append((info["pid"], info["name"], mem_mb, info["cpu_percent"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        top_procs.sort(key=lambda x: x[2], reverse=True)
        top_str = "\n".join(f" - PID {p[0]:<6} | {p[1]:<25} | RAM: {p[2]} MB | CPU: {p[3]}%" for p in top_procs[:top_n])

        return (
            f"🖥️ SYSTEM DIAGNOSTICS & TELEMETRY:\n"
            f" - CPU Load: {cpu_pct}%\n"
            f" - Memory Usage: {mem.percent}% ({round(mem.used / (1024**3), 2)} GB / {round(mem.total / (1024**3), 2)} GB)\n"
            f" - Disk Usage: {disk.percent}% ({round(disk.used / (1024**3), 2)} GB / {round(disk.total / (1024**3), 2)} GB)\n\n"
            f"🔥 TOP {top_n} MEMORY CONSUMING PROCESSES:\n{top_str}"
        )
    else:
        return "System telemetry unavailable (psutil required)."


@register_tool(
    name="kill_process",
    description="Kill or terminate a running process by Process ID (PID) or process name.",
    parameters={
        "type": "object",
        "properties": {
            "identifier": {"type": "string", "description": "PID (e.g. '1234') or Process Name (e.g. 'notepad.exe')"}
        },
        "required": ["identifier"],
    },
)
def kill_process(args: dict) -> str:
    """Kill process by PID or name."""
    identifier = str(args.get("identifier", "")).strip()
    if not identifier:
        return "Error: Process identifier required."

    if sys.platform == "win32":
        if identifier.isdigit():
            cmd = ["taskkill", "/F", "/PID", identifier]
        else:
            cmd = ["taskkill", "/F", "/IM", identifier]
        try:
            res = subprocess.run(
                cmd, shell=False, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15
            )

            if res.returncode == 0:
                return f"Successfully terminated process '{identifier}'."
            return f"Failed to kill process: {res.stderr.strip()}"
        except Exception as e:
            return f"Process termination error: {e}"
    else:
        return f"Process termination command executed for '{identifier}'."
