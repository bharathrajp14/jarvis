# tools/app_analyzer_tools.py — BR-Jarvis System Application Analyzer Tools Plugin
"""
System Application Analyzer Tools Plugin for JARVIS.
Exposes tools for scanning installed software and running process applications.
"""
from __future__ import annotations

import json
from typing import Any, Dict
from tools.registry import register_tool
# NOTE: get_app_analyzer is imported lazily inside each handler to prevent a
# missing/broken actions.app_analyzer from silently killing all tool registrations.


@register_tool(
    name="list_installed_applications",
    description="Scan and list all installed applications on the system (Windows Registry/Start Menu, macOS Apps, Linux desktop files). Args: optional 'query' filter string.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional keyword filter to search app names"},
            "limit": {"type": "integer", "description": "Maximum number of apps to return (default: 50)"}
        }
    }
)
def tool_list_installed_applications(args: dict) -> str:
    """List installed applications on the host system."""
    from actions.app_analyzer import get_app_analyzer  # lazy import
    query = str(args.get("query", "")).strip().lower()
    limit = args.get("limit", 50)

    analyzer = get_app_analyzer()
    apps = analyzer.scan_installed_apps()

    if query:
        apps = [a for a in apps if query in a["name"].lower() or query in a["path"].lower()]

    total_count = len(apps)
    apps_pruned = apps[:limit]

    output = [f"💻 INSTALLED APPLICATIONS ({len(apps_pruned)} shown / {total_count} total):"]
    for app in apps_pruned:
        path_str = f" | Path: {app['path']}" if app['path'] else ""
        ver_str = f" | Ver: {app['version']}" if app['version'] != "N/A" else ""
        output.append(f" - [{app['source']}] {app['name']}{ver_str}{path_str}")

    return "\n".join(output)


@register_tool(
    name="list_running_applications",
    description="List all active running desktop applications and processes on the system with PID, Memory usage, CPU %, and Path.",
    parameters={
        "type": "object",
        "properties": {
            "gui_only": {"type": "boolean", "description": "Whether to filter system background noise (default: true)"},
            "top_n": {"type": "integer", "description": "Number of top running apps to display (default: 25)"}
        }
    }
)
def tool_list_running_applications(args: dict) -> str:
    """List running desktop applications and processes."""
    from actions.app_analyzer import get_app_analyzer  # lazy import
    gui_only = args.get("gui_only", True)
    top_n = args.get("top_n", 25)

    analyzer = get_app_analyzer()
    running = analyzer.get_running_apps(filter_gui_only=gui_only)

    output = [f"⚡ RUNNING APPLICATIONS & PROCESSES ({min(len(running), top_n)} of {len(running)} active):"]
    for proc in running[:top_n]:
        path_str = f" | Exe: {proc['exe_path']}" if proc['exe_path'] else ""
        output.append(f" - PID {proc['pid']:<6} | {proc['name']:<25} | RAM: {proc['memory_mb']} MB | CPU: {proc['cpu_percent']}%{path_str}")

    return "\n".join(output)


@register_tool(
    name="search_applications",
    description="Search both installed and currently running applications on the system by keyword.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Application name or keyword to search for"}
        },
        "required": ["query"]
    }
)
def tool_search_applications(args: dict) -> str:
    """Search installed and running applications by keyword."""
    from actions.app_analyzer import get_app_analyzer  # lazy import
    query = str(args.get("query", "")).strip()
    if not query:
        return "Error: Search query required."

    analyzer = get_app_analyzer()
    res = analyzer.search_apps(query)

    installed = res["installed_matches"]
    running = res["running_matches"]

    lines = [f"🔍 APPLICATION SEARCH RESULTS FOR '{query}':\n"]
    lines.append(f"📦 Installed App Matches ({len(installed)}):")
    if installed:
        for app in installed[:15]:
            lines.append(f"  - [{app['source']}] {app['name']} (Path: {app['path']})")
    else:
        lines.append("  (No installed applications matched)")

    lines.append(f"\n⚡ Running App Matches ({len(running)}):")
    if running:
        for proc in running[:15]:
            lines.append(f"  - PID {proc['pid']} | {proc['name']} | RAM: {proc['memory_mb']} MB")
    else:
        lines.append("  (No running processes matched)")

    return "\n".join(lines)


@register_tool(
    name="sync_app_paths",
    description="Automatically scan host OS (Windows Registry, Start Menu, LocalAppData, Program Files) and configure/index all application executable paths into config/app_paths.json.",
    parameters={"type": "object", "properties": {}}
)
def tool_sync_app_paths(args: dict) -> str:
    """Rescan and auto-configure all system application executable paths."""
    from actions.app_resolver import get_app_resolver
    resolver = get_app_resolver()
    apps = resolver.rescan_system_applications()
    return f"✅ Successfully scanned and auto-configured {len(apps)} system application paths into config/app_paths.json."

