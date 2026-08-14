# tools/system_diagnostic_tool.py — OS Telemetry & Diagnostic Tool for JARVIS MK37
"""
Provides real-time system resource monitoring, memory/CPU pressure auditing,
disk usage analysis, and network port inspection.
"""
from __future__ import annotations

import logging
import os
import sys
import psutil
import socket
import platform
from tools.registry import register_tool

logger = logging.getLogger(__name__)


@register_tool(
    name="system_diagnostic",
    description="Inspect system health, CPU/RAM usage, top memory-hogging processes, disk space, and open network sockets.",
    parameters={
        "type": "object",
        "properties": {
            "aspect": {
                "type": "string",
                "enum": ["full_summary", "cpu_ram", "top_processes", "disk_io", "network_ports"],
                "description": "System telemetry aspect to query"
            },
            "top_n": {"type": "integer", "description": "Number of top processes to return (default: 5)"}
        },
        "required": ["aspect"]
    }
)
def system_diagnostic(args: dict) -> str:
    aspect = args.get("aspect", "full_summary")
    top_n = args.get("top_n", 5)

    if aspect == "cpu_ram":
        cpu_pct = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return (
            f"💻 CPU & Memory Status:\n"
            f"- CPU Usage: {cpu_pct}% ({cpu_count} logical cores)\n"
            f"- RAM Usage: {mem.percent}% ({mem.used / (1024**3):.2f} GB / {mem.total / (1024**3):.2f} GB used)\n"
            f"- Swap Usage: {swap.percent}% ({swap.used / (1024**3):.2f} GB / {swap.total / (1024**3):.2f} GB used)"
        )

    elif aspect == "top_processes":
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
            try:
                info = p.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by memory percent
        procs_by_mem = sorted(procs, key=lambda x: x['memory_percent'] or 0, reverse=True)[:top_n]
        out = [f"🔥 Top {top_n} Memory-Consuming Processes:"]
        for p in procs_by_mem:
            rss_mb = (p['memory_info'].rss / (1024**2)) if p.get('memory_info') else 0
            out.append(f"  ● PID {p['pid']:<6} | {p['name']:<25} | RAM: {rss_mb:.1f} MB ({p['memory_percent']:.1f}%) | CPU: {p['cpu_percent'] or 0:.1f}%")
        return "\n".join(out)

    elif aspect == "disk_io":
        disks = psutil.disk_partitions()
        out = ["💾 Disk Partition Usage:"]
        for d in disks:
            try:
                usage = psutil.disk_usage(d.mountpoint)
                out.append(f"  ● Drive {d.mountpoint:<6} ({d.fstype or 'N/A'}) -> Used: {usage.percent}% ({usage.used / (1024**3):.1f} GB / {usage.total / (1024**3):.1f} GB)")
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
        return "\n".join(out)

    elif aspect == "network_ports":
        conns = []
        try:
            for c in psutil.net_connections(kind='inet'):
                if c.status == 'LISTEN':
                    laddr = f"{c.laddr.ip}:{c.laddr.port}"
                    conns.append(f"  ● Port {c.laddr.port:<5} | PID {c.pid or 'N/A':<6} | Address: {laddr}")
            if not conns:
                return "🌐 Listening Sockets: None found or elevated privileges required."
            return "🌐 Active Listening Ports:\n" + "\n".join(conns[:15])
        except Exception as e:
            return f"Network sockets query error: {e}"

    elif aspect == "full_summary":
        cpu_pct = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        uname = platform.uname()
        return (
            f"🖥️ System Health Overview ({uname.system} {uname.release}):\n"
            f"- Host: {uname.node}\n"
            f"- CPU: {cpu_pct}% ({psutil.cpu_count()} cores)\n"
            f"- RAM: {mem.percent}% ({mem.used / (1024**3):.2f} / {mem.total / (1024**3):.2f} GB)\n"
            f"- Python: {sys.version.split()[0]}\n"
            f"- System Uptime: {(psutil.time.time() - psutil.boot_time()) / 3600:.1f} hours"
        )

    return f"Unknown aspect '{aspect}'."
