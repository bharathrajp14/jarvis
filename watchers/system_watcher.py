# watchers/system_watcher.py — Event-Driven System & OS Telemetry Watcher
"""
SystemWatcher monitors system metrics (CPU, RAM, active window) and emits telemetry events.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional
from events.bus import get_event_bus

logger = logging.getLogger("JARVIS.SystemWatcher")


class SystemWatcher:
    """
    Event-driven system telemetry watcher emitting CPU/RAM threshold alerts to EventBus.
    """

    def __init__(self):
        self.event_bus = get_event_bus()
        try:
            import psutil
            psutil.cpu_percent(interval=None)  # Warm-up initial CPU sample
        except Exception:
            pass

    def check_telemetry(self) -> Dict[str, Any]:
        """
        Sample system telemetry and publish events if thresholds are exceeded.
        """
        metrics = {"timestamp": time.time(), "status": "nominal"}

        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()

            metrics["cpu_percent"] = cpu_percent
            metrics["ram_percent"] = ram.percent

            if cpu_percent > 90.0:
                logger.warning(f"⚠️ SystemWatcher: High CPU load detected ({cpu_percent}%)")
                self.event_bus.publish("system.high_cpu", {"cpu_percent": cpu_percent})

            if ram.percent > 90.0:
                logger.warning(f"⚠️ SystemWatcher: High RAM usage detected ({ram.percent}%)")
                self.event_bus.publish("system.high_ram", {"ram_percent": ram.percent})
        except Exception:
            pass

        return metrics
