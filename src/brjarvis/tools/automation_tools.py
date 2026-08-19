# tools/automation_tools.py — BR-Jarvis Automation Engine Tools Plugin
"""
Automation Engine Tools Plugin for JARVIS.
Exposes application automation, workflow macro scripting, and system command automation tools.
"""

from __future__ import annotations

import json

from .registry import register_tool

# NOTE: get_automation_engine is imported lazily inside each handler to prevent a
# missing/broken actions.automation_engine from silently killing all tool registrations.


@register_tool(
    name="automate_app",
    description="Perform application lifecycle automation actions: 'launch', 'close', or 'focus'. Args: 'action' ('launch', 'close', or 'focus'), 'app_name' (application name or window title), 'url' (optional target URL).",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["launch", "close", "focus"], "description": "Action to perform"},
            "app_name": {"type": "string", "description": "Application name, executable name, PID, or window title"},
            "url": {"type": "string", "description": "Optional web URL if opening a browser app"},
        },
        "required": ["action", "app_name"],
    },
)
def tool_automate_app(args: dict) -> str:
    """Perform application control action."""
    from brjarvis.actions.automation_engine import get_automation_engine  # lazy import

    action = str(args.get("action", "")).strip().lower()
    app_name = str(args.get("app_name", "")).strip()
    url = str(args.get("url", "")).strip()

    if not action or not app_name:
        return "Error: Both 'action' and 'app_name' are required."

    engine = get_automation_engine()

    if action in ("launch", "open"):
        return engine.launch_app(app_name, url=url)
    elif action in ("close", "kill", "terminate"):
        return engine.close_app(app_name)
    elif action in ("focus", "switch"):
        return engine.focus_app(app_name)
    else:
        return f"Unknown application action '{action}'. Valid actions: launch, close, focus."


@register_tool(
    name="run_automation_workflow",
    description="Execute a multi-step macro automation workflow script. Pass steps as a JSON list or array of action objects (e.g. launch_app, sleep, type_text, hotkey, shell).",
    parameters={
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "description": "List of step dictionary objects. Example: [{'action': 'launch_app', 'app_name': 'notepad'}, {'action': 'sleep', 'seconds': 1}, {'action': 'type_text', 'text': 'Hello World'}]",
                "items": {"type": "object"},
            }
        },
        "required": ["steps"],
    },
)
def tool_run_automation_workflow(args: dict) -> str:
    """Execute a multi-step macro workflow script."""
    from brjarvis.actions.automation_engine import get_automation_engine  # lazy import

    raw_steps = args.get("steps", [])

    if isinstance(raw_steps, str):
        try:
            raw_steps = json.loads(raw_steps)
        except Exception as e:
            return f"Error parsing steps JSON: {e}"

    if not isinstance(raw_steps, list) or not raw_steps:
        return "Error: 'steps' must be a non-empty list of action objects."

    engine = get_automation_engine()
    res = engine.run_workflow_script(raw_steps)

    status_icon = "✅" if res["success"] else "⚠️"
    lines = [f"{status_icon} WORKFLOW AUTOMATION EXECUTED ({res['step_count']} steps):\n"]
    for item in res["results"]:
        for step_name, step_out in item.items():
            lines.append(f"  ● {step_name}: {step_out}")

    return "\n".join(lines)


@register_tool(
    name="execute_system_automation",
    description="Execute automated PowerShell or system shell command scripts with timeout and output capture.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command line or PowerShell snippet to execute"},
            "timeout": {"type": "integer", "description": "Maximum execution time in seconds (default: 30)"},
        },
        "required": ["command"],
    },
)
def tool_execute_system_automation(args: dict) -> str:
    """Execute system command automation."""
    from brjarvis.actions.automation_engine import get_automation_engine  # lazy import

    command = str(args.get("command", "")).strip()
    timeout = args.get("timeout", 30)

    if not command:
        return "Error: Command is required."

    engine = get_automation_engine()
    res = engine.execute_shell(command, timeout=timeout)

    icon = "✅" if res["success"] else "❌"
    return f"{icon} System Automation Command (Return Code: {res['returncode']}):\n{res['output']}"
