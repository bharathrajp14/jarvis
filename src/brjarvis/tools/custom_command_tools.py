# tools/custom_command_tools.py — JARVIS MK37 Custom Command Tools Plugin
"""
Registers custom command management tools in the tool registry.
"""

from __future__ import annotations

import json

from .registry import register_tool


@register_tool(
    name="custom_command_add",
    description="Add or update a custom command. You can define triggers (including variable anchors like $QUERY), aliases, and a list of actions (type: speak, open_url, open_app, run_command, press_keys, hotkey).",
    parameters={
        "type": "object",
        "properties": {
            "trigger": {"type": "string", "description": "Trigger phrase, e.g., 'search google for $QUERY'"},
            "aliases": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of alias triggers",
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Action type: speak, open_url, open_app, run_command, press_keys, hotkey",
                        },
                        "text": {
                            "type": "string",
                            "description": "The target text, URL, app name, command, or keys to type",
                        },
                    },
                    "required": ["type"],
                },
                "description": "Sequential actions to execute",
            },
        },
        "required": ["trigger", "actions"],
    },
)
def tool_custom_command_add(args: dict) -> str:
    from brjarvis.actions.custom_commands import custom_command_engine

    # Normalize actions text keys
    actions = []
    for act in args["actions"]:
        a = {"type": act["type"]}
        val = act.get("text", act.get("url", act.get("name", act.get("cmd", ""))))
        a["text"] = val
        actions.append(a)

    result = custom_command_engine.add_command(
        trigger=args["trigger"],
        actions=actions,
        aliases=args.get("aliases"),
    )
    return result


@register_tool(
    name="custom_command_list", description="List all user-configured custom voice and text commands.", parameters={}
)
def tool_custom_command_list(args: dict) -> str:
    from brjarvis.actions.custom_commands import custom_command_engine

    return json.dumps(custom_command_engine.commands, indent=2)


@register_tool(
    name="custom_command_delete",
    description="Delete a custom command using its trigger phrase.",
    parameters={
        "type": "object",
        "properties": {
            "trigger": {"type": "string", "description": "The exact trigger phrase of the command to delete"},
        },
        "required": ["trigger"],
    },
)
def tool_custom_command_delete(args: dict) -> str:
    from brjarvis.actions.custom_commands import custom_command_engine

    return custom_command_engine.delete_command(args["trigger"])
