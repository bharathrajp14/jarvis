# tools/system_health.py — System Health & Performance Monitoring Tool for JARVIS
"""
System Health & Telemetry tool for JARVIS.
Monitors CPU load, RAM memory usage, process count, disk storage, and battery status.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Any


def get_system_health() -> Dict[str, Any]:
    """Retrieve current system performance and hardware state."""
    health: Dict[str, Any] = {
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
        "cpu_count": os.cpu_count() or 1,
    }

    try:
        import psutil
        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)
        disk = psutil.disk_usage("/")

        health["cpu_usage_percent"] = cpu_pct
        health["ram_total_gb"] = round(vm.total / (1024 ** 3), 2)
        health["ram_used_gb"] = round(vm.used / (1024 ** 3), 2)
        health["ram_usage_percent"] = vm.percent
        health["disk_free_gb"] = round(disk.free / (1024 ** 3), 2)
        health["disk_usage_percent"] = disk.percent

        battery = psutil.sensors_battery()
        if battery:
            health["battery_percent"] = round(battery.percent, 1)
            health["power_plugged"] = battery.power_plugged

    except ImportError:
        health["note"] = "psutil module not installed for extended hardware metrics"

    return health


from tools.registry import register_tool


@register_tool(
    name="system_health",
    description="Retrieve system health metrics including CPU load, RAM usage, storage, and battery state.",
    parameters={
        "type": "object",
        "properties": {}
    }
)
def system_health_action(args: Dict[str, Any] = None) -> str:
    """Main tool handler for system health monitoring."""
    info = get_system_health()
    lines = ["💻 System Health & Performance Diagnostics:"]
    for k, v in info.items():
        lines.append(f"  • {k}: {v}")
    return "\n".join(lines)

