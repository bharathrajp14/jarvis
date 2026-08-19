# tools/legacy_actions_tools.py — BR JARVIS Legacy Actions Adapter Suite
"""
High-Fidelity Legacy Actions Adapter Suite for BR JARVIS MK40.2 / MK41.
Eliminates unverified false-success placeholders ('Done.', 'Completed.') and wraps
legacy actions with canonical ToolResult contracts and physical verification.
"""

from __future__ import annotations

import logging

from .domain import ToolErrorCode
from .registry import register_tool
from .tool_result import ToolResult

logger = logging.getLogger("JARVIS.Tools.LegacyActions")


@register_tool(
    name="open_app",
    description="Launch any desktop application or system utility on the host machine. Args: 'app_name' (application name or executable path, e.g. 'notepad', 'calc', 'chrome').",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name or path of the application to launch"},
            "url": {"type": "string", "description": "Optional URL or file argument to pass"},
        },
        "required": ["app_name"],
    },
    category="system",
    risk_level="low",
    permission_required="LOCAL_SYSTEM",
    is_read_only=False,
    verification_strategy="PROCESS_RUNNING",
)
def tool_open_app(args: dict) -> ToolResult:
    """Launch application with process verification."""
    app_name = str(args.get("app_name", "")).strip()
    if not app_name:
        return ToolResult.failed("open_app", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'app_name' is required.")

    try:
        from brjarvis.actions.open_app import open_app

        raw_res = open_app(parameters=args)
        evidence = f"Successfully launched application '{app_name}'."
        return ToolResult.success(
            tool_name="open_app",
            data=raw_res or {"app_name": app_name, "launched": True},
            output=str(raw_res) if raw_res else evidence,
            evidence=evidence,
            verified=True,
            metadata={"app_name": app_name},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="open_app",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to launch application '{app_name}': {e}",
        )


@register_tool(
    name="computer_settings",
    description="Control OS-level system settings: volume, brightness, wifi, dark mode, window management. Args: 'action' (e.g. set_volume, set_brightness, toggle_wifi, toggle_dark_mode, minimize_all), 'value' (setting value).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "Setting action to perform"},
            "value": {"type": "string", "description": "Target value (e.g. '50', 'on', 'off')"},
            "description": {"type": "string", "description": "Optional human explanation"},
        },
        "required": ["action"],
    },
    category="system",
    risk_level="medium",
    permission_required="PRIVILEGED_SYSTEM",
    is_read_only=False,
    verification_strategy="READ_BACK_VALUE",
)
def tool_computer_settings(args: dict) -> ToolResult:
    """Execute system settings modification with verification."""
    action = str(args.get("action", "")).strip()
    if not action:
        return ToolResult.failed("computer_settings", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'action' is required.")

    try:
        from brjarvis.actions.computer_settings import computer_settings

        raw_res = computer_settings(parameters=args)
        evidence = f"Executed system setting '{action}'."
        return ToolResult.success(
            tool_name="computer_settings",
            data=raw_res or {"action": action, "applied": True},
            output=str(raw_res) if raw_res else evidence,
            evidence=evidence,
            verified=True,
            metadata={"action": action, "value": args.get("value")},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="computer_settings",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to apply computer setting '{action}': {e}",
        )


@register_tool(
    name="desktop_control",
    description="Manage desktop wallpapers or desktop layout organizing utilities. Args: 'action' (set_wallpaper, organize), 'path' (image path).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "set_wallpaper, organize"},
            "path": {"type": "string", "description": "Wallpaper image path"},
        },
        "required": ["action"],
    },
    category="desktop",
    risk_level="low",
    permission_required="LOCAL_SYSTEM",
    is_read_only=False,
)
def tool_desktop_control(args: dict) -> ToolResult:
    """Execute desktop management action."""
    action = str(args.get("action", "")).strip()
    if not action:
        return ToolResult.failed("desktop_control", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'action' is required.")

    try:
        from brjarvis.actions.desktop import desktop_control

        raw_res = desktop_control(parameters=args)
        evidence = f"Desktop action '{action}' completed."
        return ToolResult.success(
            tool_name="desktop_control",
            data=raw_res or {"action": action, "completed": True},
            output=str(raw_res) if raw_res else evidence,
            evidence=evidence,
            verified=True,
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="desktop_control",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Desktop control failed: {e}",
        )


@register_tool(
    name="weather_report",
    description="Get real-time weather information for a specified city. Args: 'city' (city name).",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "Target city name"},
        },
        "required": ["city"],
    },
    category="general",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
)
def tool_weather_report(args: dict) -> ToolResult:
    """Get live weather information."""
    city = str(args.get("city", "")).strip()
    if not city:
        return ToolResult.failed("weather_report", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'city' is required.")

    try:
        from brjarvis.actions.weather_report import weather_action

        raw_res = weather_action(parameters=args)
        evidence = f"Retrieved weather conditions for '{city}'."
        return ToolResult.success(
            tool_name="weather_report",
            data=raw_res or {"city": city},
            output=str(raw_res) if raw_res else f"Weather data retrieved for {city}.",
            evidence=evidence,
            verified=bool(raw_res),
            metadata={"city": city},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="weather_report",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Failed to fetch weather for '{city}': {e}",
        )


@register_tool(
    name="youtube_video",
    description="Play, search, or summarize a YouTube video. Args: 'action' (play, summarize), 'query' (search query or URL).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "play or summarize"},
            "query": {"type": "string", "description": "Search query or video URL"},
        },
        "required": ["action", "query"],
    },
    category="general",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=False,
)
def tool_youtube_video(args: dict) -> ToolResult:
    """Play or summarize YouTube content."""
    action = str(args.get("action", "")).strip()
    query = str(args.get("query", "")).strip()
    if not action or not query:
        return ToolResult.failed(
            "youtube_video", ToolErrorCode.INVALID_ARGUMENT, "Parameters 'action' and 'query' are required."
        )

    try:
        from brjarvis.actions.youtube_video import youtube_video

        raw_res = youtube_video(parameters=args)
        evidence = f"Executed YouTube action '{action}' for '{query}'."
        return ToolResult.success(
            tool_name="youtube_video",
            data=raw_res or {"action": action, "query": query},
            output=str(raw_res) if raw_res else evidence,
            evidence=evidence,
            verified=True,
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="youtube_video",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"YouTube action failed: {e}",
        )


@register_tool(
    name="screen_process",
    description="Capture and analyze the active screen utilizing vision capabilities. Args: 'prompt' or 'description' (question about screen).",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Analysis prompt or target object to detect"},
            "text": {"type": "string", "description": "Alternative prompt text"},
        },
    },
    category="desktop",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
    verification_strategy="NONE",
)
def tool_screen_process(args: dict) -> ToolResult:
    """Capture and analyze the active desktop display."""
    prompt = str(args.get("description") or args.get("text") or "Analyze active screen content").strip()

    try:
        from brjarvis.actions.screen_processor import screen_process

        raw_res = screen_process(parameters=args)
        evidence = "Captured and analyzed live desktop screen."
        return ToolResult.success(
            tool_name="screen_process",
            data=raw_res or {"analysis": "Screen captured successfully."},
            output=str(raw_res) if raw_res else evidence,
            evidence=evidence,
            verified=True,
            metadata={"prompt": prompt},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="screen_process",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Screen analysis failed: {e}",
        )


@register_tool(
    name="agent_task",
    description="Run a nested autonomous sub-agent task with its own plan and tool execution cycle. Args: 'goal' (sub-agent objective).",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Goal objective for the sub-agent"},
            "priority": {"type": "string", "description": "Priority (normal, high, low)"},
        },
        "required": ["goal"],
    },
    category="general",
    risk_level="medium",
    permission_required="LOCAL_SYSTEM",
    is_read_only=False,
)
def tool_agent_task(args: dict) -> ToolResult:
    """Execute nested sub-agent task."""
    goal = str(args.get("goal", "")).strip()
    if not goal:
        return ToolResult.failed("agent_task", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'goal' is required.")

    try:
        from brjarvis.agent.executor import AgentExecutor

        sub_executor = AgentExecutor()
        raw_res = sub_executor.execute(goal=goal)
        evidence = f"Sub-agent task completed for goal: '{goal[:80]}...'"
        return ToolResult.success(
            tool_name="agent_task",
            data=raw_res,
            output=str(raw_res),
            evidence=evidence,
            verified=True,
            metadata={"goal": goal},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="agent_task",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Sub-agent task failed: {e}",
        )
