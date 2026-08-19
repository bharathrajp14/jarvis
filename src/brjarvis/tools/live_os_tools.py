# tools/live_os_tools.py — JARVIS MK37 Live OS Vision Control Tools Plugin
"""
Live OS Vision Control tools plugin for JARVIS MK37.
Exposes autonomous screen perception, fast reaction loop, and visual UI element tools.
"""

from __future__ import annotations

from .registry import register_tool


def _get_live_os_control():
    from brjarvis.actions.live_os_control import live_os_control_action

    return live_os_control_action


def _get_computer_control():
    from brjarvis.actions.computer_control import computer_control

    return computer_control


@register_tool(
    name="live_os_control",
    description="Launch autonomous Live OS Visual Control loop ('Antigravity Mode'). Performs real-time screen perception, planning, and mouse/keyboard action execution until goal is achieved.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Objective or task to accomplish on the computer desktop."},
            "max_steps": {"type": "integer", "description": "Maximum step limit (default 20)."},
        },
        "required": ["goal"],
    },
)
def tool_live_os_control(args: dict) -> str:
    loc = _get_live_os_control()
    return loc(parameters={"goal": args["goal"], "max_steps": args.get("max_steps", 20)})


@register_tool(
    name="live_screen_analyze",
    description="Analyze the current screen using vision AI and return a structured visual breakdown of open windows, interactive UI elements, and desktop state.",
    parameters={},
)
def tool_live_screen_analyze(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screen_describe"})


@register_tool(
    name="visual_click",
    description="Use AI vision to locate a specific UI element by description on the screen and click it.",
    parameters={
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Visual description of element (e.g., 'blue submit button', 'Chrome browser icon', 'search bar').",
            },
        },
        "required": ["description"],
    },
)
def tool_visual_click(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screen_click", "description": args["description"]})


@register_tool(
    name="visual_type",
    description="Use AI vision to locate an input field by description and type text into it.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Visual description of input box or field."},
            "text": {"type": "string", "description": "Text to type into the field."},
        },
        "required": ["description", "text"],
    },
)
def tool_visual_type(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "smart_type_elem", "description": args["description"], "text": args["text"]})


@register_tool(
    name="visual_drag",
    description="Click and drag from a source UI element to a target UI element identified by visual description.",
    parameters={
        "type": "object",
        "properties": {
            "from_description": {"type": "string", "description": "Visual description of source element."},
            "to_description": {"type": "string", "description": "Visual description of target destination."},
        },
        "required": ["from_description", "to_description"],
    },
)
def tool_visual_drag(args: dict) -> str:
    cc = _get_computer_control()
    p1 = cc(parameters={"action": "screen_find", "description": args["from_description"]})
    p2 = cc(parameters={"action": "screen_find", "description": args["to_description"]})

    if "NOT_FOUND" in p1 or not p1:
        return f"Could not find source element: '{args['from_description']}'"
    if "NOT_FOUND" in p2 or not p2:
        return f"Could not find target element: '{args['to_description']}'"

    try:
        x1, y1 = [int(v) for v in p1.split(",")]
        x2, y2 = [int(v) for v in p2.split(",")]
        return cc(parameters={"action": "drag", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
    except Exception as e:
        return f"Drag failed: {e}"
