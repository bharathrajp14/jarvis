# tools/legacy_actions_tools.py — JARVIS MK37 Legacy Actions Tools Plugin
"""
Plugin registering legacy action controllers from the actions/ folder.
Unified integration for both ReAct loop and AgentExecutor.
"""
from __future__ import annotations

from .registry import register_tool


@register_tool(
    name="open_app",
    description="Launch any application on the host machine.",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name or path of the application to launch"},
        },
        "required": ["app_name"],
    }
)
def tool_open_app(args: dict) -> str:
    from brjarvis.actions.open_app import open_app
    return open_app(parameters=args) or "Done."


@register_tool(
    name="game_updater",
    description="Manage Steam/Epic games (updating, launching, checking status).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "launch, update, status"},
            "platform": {"type": "string", "description": "steam, epic"},
            "game_name": {"type": "string"},
        },
        "required": ["action", "platform", "game_name"],
    }
)
def tool_game_updater(args: dict) -> str:
    from brjarvis.actions.game_updater import game_updater
    return game_updater(parameters=args) or "Done."


@register_tool(
    name="computer_settings",
    description="Control OS-level settings: brightness, volume, wifi, dark mode, minimize/maximize.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "set_volume, set_brightness, toggle_wifi, toggle_dark_mode, minimize_all, maximize_all"},
            "description": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["action"],
    }
)
def tool_computer_settings(args: dict) -> str:
    from brjarvis.actions.computer_settings import computer_settings
    return computer_settings(parameters=args) or "Done."


@register_tool(
    name="desktop_control",
    description="Wallpaper management or desktop organizing utilities.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "set_wallpaper, organize"},
            "path": {"type": "string"},
            "task": {"type": "string"},
        },
        "required": ["action"],
    }
)
def tool_desktop_control(args: dict) -> str:
    from brjarvis.actions.desktop import desktop_control
    return desktop_control(parameters=args) or "Done."


@register_tool(
    name="weather_report",
    description="Get real-time weather information for a city.",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string"},
        },
        "required": ["city"],
    }
)
def tool_weather_report(args: dict) -> str:
    from brjarvis.actions.weather_report import weather_action
    return weather_action(parameters=args) or "Done."


@register_tool(
    name="youtube_video",
    description="Play or summarize a YouTube video.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "play, summarize"},
            "query": {"type": "string", "description": "Search query or video URL"},
        },
        "required": ["action", "query"],
    }
)
def tool_youtube_video(args: dict) -> str:
    from brjarvis.actions.youtube_video import youtube_video
    return youtube_video(parameters=args) or "Done."





@register_tool(
    name="flight_finder",
    description="Search flights details between origin and destination on a specific date.",
    parameters={
        "type": "object",
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"},
            "date": {"type": "string", "description": "Format: YYYY-MM-DD"},
        },
        "required": ["origin", "destination", "date"],
    }
)
def tool_flight_finder(args: dict) -> str:
    from brjarvis.actions.flight_finder import flight_finder
    return flight_finder(parameters=args) or "Done."


@register_tool(
    name="code_helper",
    description="Write, edit, run, or build code in specific file paths.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "write, edit, run, build"},
            "description": {"type": "string"},
            "language": {"type": "string"},
            "file_path": {"type": "string"},
        },
        "required": ["action"],
    }
)
def tool_code_helper(args: dict) -> str:
    from brjarvis.actions.code_helper import code_helper
    return code_helper(parameters=args) or "Done."


@register_tool(
    name="dev_agent",
    description="Build complete multi-file software projects autonomously.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "language": {"type": "string"},
            "project_name": {"type": "string"},
        },
        "required": ["description", "project_name"],
    }
)
def tool_dev_agent(args: dict) -> str:
    from brjarvis.actions.dev_agent import dev_agent
    return dev_agent(parameters=args) or "Done."


@register_tool(
    name="screen_process",
    description="Analyze screen or camera feed utilizing vision capabilities.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "angle": {"type": "integer"},
        },
    }
)
def tool_screen_process(args: dict) -> str:
    from brjarvis.actions.screen_processor import screen_process
    screen_process(parameters=args)
    return "Screen captured and analyzed."


@register_tool(
    name="agent_task",
    description="Complex multi-step autonomous task to run in parallel or nested.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "priority": {"type": "string", "description": "normal, high, low"},
        },
        "required": ["goal"],
    }
)
def tool_agent_task(args: dict) -> str:
    goal = args.get("goal", "")
    if not goal:
        return "No goal specified for agent_task."
    # Dynamic import to avoid circular dependencies
    from brjarvis.agent.executor import AgentExecutor
    sub_executor = AgentExecutor()
    return sub_executor.execute(goal=goal)


@register_tool(
    name="file_controller",
    description="Perform file and directory management actions (read, write, delete, move, create_dir, list).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "read, write, delete, move, create_dir, list"},
            "path": {"type": "string", "description": "Target file or directory path"},
            "name": {"type": "string", "description": "File or directory name"},
            "content": {"type": "string", "description": "Content for write operations"},
            "destination": {"type": "string", "description": "Destination path for move operations"},
        },
        "required": ["action"],
    }
)
def tool_file_controller(args: dict) -> str:
    from brjarvis.actions.file_controller import file_controller
    return file_controller(parameters=args) or "File operation completed."


