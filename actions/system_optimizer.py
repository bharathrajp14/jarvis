# actions/system_optimizer.py — Automated System, Memory & Cache Optimization Engine
"""
JARVIS Autonomous System & Memory Optimization Action.
Cleans temporary cache files, collects garbage, inspects RAM usage,
and optimizes process memory footprints.
"""
from __future__ import annotations

import logging
import gc
import os
import sys
import psutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def optimize_system_resources() -> dict:
    """
    Perform a complete system resource optimization pass:
    - Triggers Python garbage collection (gc.collect())
    - Prunes temporary TTS cache files (.mp3)
    - Measures RAM before and after optimization
    """
    process = psutil.Process(os.getpid())
    mem_before_mb = process.memory_info().rss / (1024 * 1024)

    # 1. Python GC
    collected_objects = gc.collect()

    # 2. Prune TTS Cache
    pruned_files = 0
    reclaimed_bytes = 0
    try:
        temp_dir = Path(tempfile.gettempdir()) / "br_tts_cache"
        if temp_dir.exists():
            for f in temp_dir.glob("*.mp3"):
                try:
                    reclaimed_bytes += f.stat().st_size
                    f.unlink(missing_ok=True)
                    pruned_files += 1
                except Exception as e:
                    logger.debug('Suppressed exception: %s', e)
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
    mem_after_mb = process.memory_info().rss / (1024 * 1024)
    freed_mb = max(0.0, mem_before_mb - mem_after_mb)

    # System-wide memory info
    sys_mem = psutil.virtual_memory()

    return {
        "mem_before_mb": round(mem_before_mb, 2),
        "mem_after_mb": round(mem_after_mb, 2),
        "freed_mb": round(freed_mb, 2),
        "collected_objects": collected_objects,
        "pruned_tts_files": pruned_files,
        "reclaimed_tts_mb": round(reclaimed_bytes / (1024 * 1024), 2),
        "system_ram_used_percent": sys_mem.percent,
        "system_ram_available_gb": round(sys_mem.available / (1024**3), 2),
    }


def system_optimizer_action(action: str = "optimize") -> str:
    """Tool function wrapper for system resource optimization."""
    res = optimize_system_resources()
    pruned_msg = f"{res['pruned_tts_files']} temporary TTS cache files pruned" if res['pruned_tts_files'] > 0 else "temporary cache verified clean"
    return (
        f"System optimization complete. {pruned_msg}, {res['collected_objects']} objects collected, and {res['system_ram_available_gb']} GB RAM is currently available.\n"
        f"--- Detailed Metrics ---\n"
        f"- Process Memory: {res['mem_before_mb']} MB -> {res['mem_after_mb']} MB (Freed: {res['freed_mb']} MB)\n"
        f"- Garbage Collected: {res['collected_objects']} objects\n"
        f"- Temp TTS Files Pruned: {res['pruned_tts_files']} files ({res['reclaimed_tts_mb']} MB)\n"
        f"- System RAM Usage: {res['system_ram_used_percent']}% (Available: {res['system_ram_available_gb']} GB)"
    )
