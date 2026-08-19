# tools/pc_tools.py — JARVIS MK37 OS & PC Control Tools Plugin
"""
PC and OS control tools plugin for JARVIS MK37.
Exposes mouse/keyboard/screen automation via actions.computer_control.
"""

from __future__ import annotations

from .registry import register_tool


def _get_computer_control():
    from brjarvis.actions.computer_control import computer_control

    return computer_control


@register_tool(
    name="cursor_move",
    description="Move the mouse cursor to specific screen coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"},
        },
        "required": ["x", "y"],
    },
)
def tool_cursor_move(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "move", "x": args["x"], "y": args["y"]})


@register_tool(
    name="cursor_click",
    description="Click the mouse at the current position or specified coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "button": {"type": "string", "description": "left, right, double"},
        },
    },
)
def tool_cursor_click(args: dict) -> str:
    cc = _get_computer_control()
    button = args.get("button", "left")
    action = "double_click" if button == "double" else "click"
    btn = "left" if button == "double" else button
    return cc(parameters={"action": action, "x": args.get("x"), "y": args.get("y"), "button": btn})


@register_tool(
    name="keyboard_type",
    description="Type text at the current cursor position.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "clear_first": {"type": "boolean"},
        },
        "required": ["text"],
    },
)
def tool_keyboard_type(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "smart_type", "text": args["text"], "clear_first": args.get("clear_first", True)})


@register_tool(
    name="keyboard_hotkey",
    description="Press a key combination (e.g., ctrl+c, alt+tab).",
    parameters={
        "type": "object",
        "properties": {
            "keys": {"type": "string"},
        },
        "required": ["keys"],
    },
)
def tool_keyboard_hotkey(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "hotkey", "keys": args["keys"]})


@register_tool(
    name="keyboard_press",
    description="Press a single key (enter, tab, escape, etc.).",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
        },
        "required": ["key"],
    },
)
def tool_keyboard_press(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "press", "key": args["key"]})


@register_tool(
    name="screen_find",
    description="Use AI vision to find a UI element on screen by description. Returns coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string"},
        },
        "required": ["description"],
    },
)
def tool_screen_find(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screen_find", "description": args["description"]})


@register_tool(
    name="screen_click",
    description="Find a UI element by description and click on it.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string"},
        },
        "required": ["description"],
    },
)
def tool_screen_click(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screen_click", "description": args["description"]})


@register_tool(
    name="smart_click",
    description="Smartly click a UI element by its natural language description.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string"},
        },
        "required": ["description"],
    },
)
def tool_smart_click(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screen_click", "description": args["description"]})


@register_tool(name="clipboard_read", description="Read the current clipboard content.", parameters={})
def tool_clipboard_read(args: dict) -> str:
    cc = _get_computer_control()
    res = cc(parameters={"action": "clipboard_get"})
    if not res:
        return "Clipboard is empty."
    return res


@register_tool(
    name="clipboard_write",
    description="Write text to the clipboard and paste it.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
        },
        "required": ["text"],
    },
)
def tool_clipboard_write(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "paste", "text": args["text"]})


@register_tool(
    name="focus_window",
    description="Bring a window to the foreground by title.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
        },
        "required": ["title"],
    },
)
def tool_focus_window(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "focus_window", "title": args["title"]})


@register_tool(
    name="take_screenshot",
    description="Capture a screenshot of the current screen.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
        },
    },
)
def tool_take_screenshot(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screenshot", "path": args.get("path")})


@register_tool(
    name="mouse_scroll",
    description="Scroll the mouse wheel.",
    parameters={
        "type": "object",
        "properties": {
            "direction": {"type": "string"},
            "amount": {"type": "integer"},
        },
    },
)
def tool_mouse_scroll(args: dict) -> str:
    cc = _get_computer_control()
    return cc(
        parameters={"action": "scroll", "direction": args.get("direction", "down"), "amount": args.get("amount", 3)}
    )


@register_tool(
    name="mouse_drag",
    description="Click and drag from one point to another.",
    parameters={
        "type": "object",
        "properties": {
            "x1": {"type": "integer"},
            "y1": {"type": "integer"},
            "x2": {"type": "integer"},
            "y2": {"type": "integer"},
        },
        "required": ["x1", "y1", "x2", "y2"],
    },
)
def tool_mouse_drag(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "drag", "x1": args["x1"], "y1": args["y1"], "x2": args["x2"], "y2": args["y2"]})


@register_tool(name="screen_read", description="Read and OCR the entire screen via vision.", parameters={})
def tool_screen_read(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screen_read"})


@register_tool(
    name="screen_describe", description="Get a natural language description of what is on the screen.", parameters={}
)
def tool_screen_describe(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters={"action": "screen_describe"})


@register_tool(
    name="wait_for_element",
    description="Wait until a UI element appears on screen.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "timeout": {"type": "integer"},
        },
        "required": ["description"],
    },
)
def tool_wait_for_element(args: dict) -> str:
    cc = _get_computer_control()
    return cc(
        parameters={
            "action": "wait_for_element",
            "description": args["description"],
            "timeout": args.get("timeout", 10),
        }
    )


@register_tool(
    name="window_maximize",
    description="Maximize a window by title or process name.",
    parameters={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
)
def tool_window_maximize(args: dict) -> str:
    import subprocess

    title = args.get("title", "")
    try:
        subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", title, "windowactivate", "windowmaximize"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Maximized window matching '{title}'"
    except Exception:
        return f"Window maximize requested for '{title}'"


@register_tool(
    name="window_minimize",
    description="Minimize a window by title or process name.",
    parameters={"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
)
def tool_window_minimize(args: dict) -> str:
    import subprocess

    title = args.get("title", "")
    try:
        subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", title, "windowminimize"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Minimized window matching '{title}'"
    except Exception:
        return f"Window minimize requested for '{title}'"


@register_tool(
    name="cursor_get_position", description="Get current mouse cursor (X, Y) coordinates on screen.", parameters={}
)
def tool_cursor_get_position(args: dict) -> str:
    try:
        import pyautogui

        x, y = pyautogui.position()
        return f'{{"x": {x}, "y": {y}}}'
    except Exception:
        return '{"x": 0, "y": 0}'


@register_tool(name="display_resolution", description="Query screen display dimensions (width, height).", parameters={})
def tool_display_resolution(args: dict) -> str:
    try:
        import pyautogui

        w, h = pyautogui.size()
        return f'{{"width": {w}, "height": {h}}}'
    except Exception:
        return '{"width": 1920, "height": 1080}'


@register_tool(
    name="keyboard_key_down",
    description="Press and hold a specific key down.",
    parameters={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
)
def tool_keyboard_key_down(args: dict) -> str:
    try:
        import pyautogui

        pyautogui.keyDown(args.get("key", ""))
        return f"Key '{args.get('key')}' pressed down"
    except Exception as e:
        return f"keyDown error: {e}"


@register_tool(
    name="keyboard_key_up",
    description="Release a held key.",
    parameters={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
)
def tool_keyboard_key_up(args: dict) -> str:
    try:
        import pyautogui

        pyautogui.keyUp(args.get("key", ""))
        return f"Key '{args.get('key')}' released"
    except Exception as e:
        return f"keyUp error: {e}"


@register_tool(
    name="computer_control",
    description="Mouse, keyboard, and screen automation engine (click, move, drag, type, hotkey, press, scroll, screenshot, screen_find, screen_click).",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "type, smart_type, click, double_click, right_click, move, drag, hotkey, press, scroll, copy, paste, screenshot, wait, clear_field, focus_window, screen_find, screen_click, random_data, user_data",
            },
            "text": {"type": "string"},
            "x": {"type": "number"},
            "y": {"type": "number"},
            "x1": {"type": "number"},
            "y1": {"type": "number"},
            "x2": {"type": "number"},
            "y2": {"type": "number"},
            "keys": {"type": "string"},
            "key": {"type": "string"},
            "direction": {"type": "string"},
            "amount": {"type": "number"},
            "seconds": {"type": "number"},
            "title": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["action"],
    },
)
def tool_computer_control(args: dict) -> str:
    cc = _get_computer_control()
    return cc(parameters=args)
