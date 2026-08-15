# tools/system_tools.py — JARVIS MK37 System & CLI Tools Plugin
"""
System, CLI controller, and screen sharing tools plugin for JARVIS MK37.
"""
from __future__ import annotations

import json
from tools.registry import register_tool


@register_tool(
    name="cli_controller",
    description="Full terminal/shell access. Run ANY shell command, manage persistent shell sessions with state (env vars, cwd), execute Python code, send input to interactive programs, manage background processes. Actions: run, run_session, send_input, cd, pwd, python, pipe, bg, which, env, session_new, session_end, history, auto.",
    parameters={
        "type": "object",
        "properties": {
            "action":  {"type": "string"},
            "cmd":     {"type": "string"},
            "name":    {"type": "string"},
            "cwd":     {"type": "string"},
            "timeout": {"type": "integer"},
            "key":     {"type": "string"},
            "value":   {"type": "string"},
            "code":    {"type": "string"},
        },
        "required": ["action"],
    }
)
def tool_cli_controller(args: dict) -> str:
    try:
        from actions.cli_controller import cli_controller
        return str(cli_controller(parameters=args))
    except ImportError:
        return "ERROR: cli_controller not installed"


@register_tool(
    name="system_monitor",
    description="Get system health info: CPU, RAM, disk, network, top processes.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string"},
        },
    }
)
def tool_system_monitor(args: dict) -> str:
    from actions.system_monitor import system_monitor
    return system_monitor(parameters=args)


@register_tool(
    name="screen_share_start",
    description="Start real-time screen sharing over WebSocket.",
    parameters={
        "type": "object",
        "properties": {
            "port": {"type": "integer"},
            "monitor": {"type": "integer"},
            "fps": {"type": "integer"},
            "quality": {"type": "integer"},
        },
    }
)
def tool_screen_share_start(args: dict) -> str:
    from actions.screen_share import start_sharing
    return start_sharing(
        port=args.get("port", 8765),
        monitor=args.get("monitor", 1),
        fps=args.get("fps", 10),
        quality=args.get("quality", 60),
    )


@register_tool(
    name="screen_share_stop",
    description="Stop the active screen sharing session.",
    parameters={}
)
def tool_screen_share_stop(args: dict) -> str:
    from actions.screen_share import stop_sharing
    return stop_sharing()


@register_tool(
    name="screen_share_status",
    description="Get the current screen sharing status.",
    parameters={}
)
def tool_screen_share_status(args: dict) -> str:
    from actions.screen_share import get_status
    return json.dumps(get_status(), indent=2)


@register_tool(
    name="list_monitors",
    description="List all available monitors with resolution and position.",
    parameters={}
)
def tool_list_monitors(args: dict) -> str:
    from actions.screen_share import list_monitors
    return json.dumps(list_monitors(), indent=2)


@register_tool(
    name="native_hash_fast",
    description="High-speed C-native FNV-1a hashing for screen frame delta detection or content integrity.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        },
        "required": ["text"]
    }
)
def tool_native_hash_fast(args: dict) -> str:
    from core.native_bridge import fast_hash
    text = args.get("text", "")
    h = fast_hash(text.encode("utf-8") if isinstance(text, str) else text)
    return json.dumps({"hash": h, "hex": hex(h)})


@register_tool(
    name="native_audio_meter",
    description="High-speed C-native RMS audio energy calculator for microphone and voice level monitoring.",
    parameters={
        "type": "object",
        "properties": {
            "samples": {"type": "array", "items": {"type": "number"}}
        },
        "required": ["samples"]
    }
)
def tool_native_audio_meter(args: dict) -> str:
    from core.native_bridge import audio_energy
    samples = args.get("samples", [0.0])
    rms = audio_energy(samples)
    return json.dumps({"rms_energy": rms})


@register_tool(
    name="native_grid_transform",
    description="Transform target visual grid coordinates to screen pixel coordinates via C extension.",
    parameters={
        "type": "object",
        "properties": {
            "gx": {"type": "integer"},
            "gy": {"type": "integer"},
            "grid_size": {"type": "integer"},
            "sw": {"type": "integer"},
            "sh": {"type": "integer"}
        },
        "required": ["gx", "gy", "sw", "sh"]
    }
)
def tool_native_grid_transform(args: dict) -> str:
    from core.native_bridge import grid_transform
    gx = int(args.get("gx", 0))
    gy = int(args.get("gy", 0))
    gs = int(args.get("grid_size", 1000))
    sw = int(args.get("sw", 1920))
    sh = int(args.get("sh", 1080))
    x, y = grid_transform(gx, gy, gs, sw, sh)
    return json.dumps({"x": x, "y": y})


@register_tool(
    name="native_proc_telemetry",
    description="Low-overhead C-native process page count and RAM usage reader.",
    parameters={
        "type": "object",
        "properties": {
            "pid": {"type": "integer"}
        }
    }
)
def tool_native_proc_telemetry(args: dict) -> str:
    from core.native_bridge import proc_memory_kb
    import os
    pid = int(args.get("pid", os.getpid()))
    kb = proc_memory_kb(pid)
    return json.dumps({"pid": pid, "memory_kb": kb, "memory_mb": round(kb / 1024.0, 2)})


@register_tool(
    name="system_cleanup",
    description="Clean temporary cache files, old log files, and build artifacts to reclaim disk space.",
    parameters={
        "type": "object",
        "properties": {
            "clean_temp": {"type": "boolean", "default": True},
            "clean_pycache": {"type": "boolean", "default": True},
            "clean_logs": {"type": "boolean", "default": False}
        }
    }
)
def tool_system_cleanup(args: dict) -> str:
    try:
        from actions.system_cleanup import execute_system_cleanup
        return execute_system_cleanup(
            clean_temp=args.get("clean_temp", True),
            clean_pycache=args.get("clean_pycache", True),
            clean_logs=args.get("clean_logs", False)
        )
    except Exception:
        import shutil
        import tempfile
        from pathlib import Path
        reclaimed_bytes = 0
        removed_count = 0
        if args.get("clean_pycache", True):
            for p in Path(".").rglob("__pycache__"):
                try:
                    reclaimed_bytes += sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
                    shutil.rmtree(p)
                    removed_count += 1
                except Exception:
                    pass
        if args.get("clean_temp", True):
            temp_dir = Path(tempfile.gettempdir())
            try:
                for item in temp_dir.iterdir():
                    if item.is_file() and item.name.startswith("tmp"):
                        try:
                            reclaimed_bytes += item.stat().st_size
                            item.unlink()
                            removed_count += 1
                        except Exception:
                            pass
            except Exception:
                pass
        return f"Cleaned {removed_count} temporary items ({reclaimed_bytes / (1024*1024):.2f} MB freed)."


@register_tool(
    name="system_optimizer",
    description="Analyze and optimize CPU, RAM, and background task consumption.",
    parameters={
        "type": "object",
        "properties": {
            "aggressive": {"type": "boolean", "default": False}
        }
    }
)
def tool_system_optimizer(args: dict) -> str:
    try:
        from actions.system_optimizer import optimize_system_resources
        res = optimize_system_resources()
        if isinstance(res, dict):
            return f"System Optimized: Freed {res.get('freed_mb', 0)} MB RAM, collected {res.get('collected_objects', 0)} GC objects."
        return str(res)
    except Exception:
        import gc
        import psutil
        proc = psutil.Process(os.getpid())
        mem_before = proc.memory_info().rss / (1024 * 1024)
        collected = gc.collect()
        mem_after = proc.memory_info().rss / (1024 * 1024)
        freed = max(0.0, mem_before - mem_after)
        return f"System Optimized: Freed {freed:.2f} MB RAM ({collected} objects collected)."



