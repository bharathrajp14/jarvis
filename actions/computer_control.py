"""
JARVIS MK37 — Enhanced Computer Control (actions/computer_control.py)
Full operating system control: mouse, keyboard, clipboard, screen,
window management, AI-powered element detection, and OCR.
"""
from __future__ import annotations

import io
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import string
import random
from pathlib import Path

# ── Optional imports ──────────────────────────────────────────────────────────
from actions.clipboard_utils import get_clipboard_text, set_clipboard_text

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.04
    _PYAUTOGUI = True
except Exception:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except Exception:
    _PYPERCLIP = False

try:
    import pygetwindow as gw
    _PYGW = True
except Exception:
    _PYGW = False

try:
    import PIL.Image as PILImage
    import PIL.ImageGrab as PILGrab
    _PIL = True
except Exception:
    _PIL = False

_OS = platform.system()


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"
_MEMORY_PATH = _BASE / "memory" / "long_term.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_api_key() -> str:
    for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(env, "").strip()
        if val:
            return val
    return _load_config().get("gemini_api_key", "")



# ── Screen resolution ─────────────────────────────────────────────────────────

def _screen_size() -> tuple[int, int]:
    try:
        import mss
        with mss.mss() as s:
            mon = s.monitors[1] if len(s.monitors) > 1 else s.monitors[0]
            if mon["width"] > 0 and mon["height"] > 0:
                return mon["width"], mon["height"]
    except Exception:
        pass

    if _PYAUTOGUI:
        try:
            s = pyautogui.size()
            if s.width > 0 and s.height > 0:
                return s.width, s.height
        except Exception:
            pass

    if _PIL:
        try:
            img = PILGrab.grab()
            return img.size
        except Exception:
            pass

    if _OS == "Linux":
        try:
            res = subprocess.run(["xrandr"], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=3)
            import re
            m = re.search(r"current\s+(\d+)\s+x\s+(\d+)", res.stdout)
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception:
            pass

        try:
            res = subprocess.run(["xdotool", "getdisplaygeometry"], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=3)
            parts = res.stdout.strip().split()
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return int(parts[0]), int(parts[1])
        except Exception:
            pass

    return 1920, 1080


# ── Screenshot ────────────────────────────────────────────────────────────────

def _take_screenshot_bytes() -> bytes:
    """Return screenshot as PNG bytes with mss, PyAutoGUI, PIL, and Linux CLI fallbacks."""
    try:
        import mss, mss.tools
        with mss.mss() as s:
            mon = s.monitors[1] if len(s.monitors) > 1 else s.monitors[0]
            shot = s.grab(mon)
            return mss.tools.to_png(shot.rgb, shot.size)
    except Exception:
        pass

    if _PYAUTOGUI:
        try:
            import io as _io
            img = pyautogui.screenshot()
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            pass

    if _PIL:
        try:
            import io as _io
            img = PILGrab.grab()
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            pass

    # Linux CLI screenshot tools fallback (scrot, import, grim)
    if _OS == "Linux":
        import tempfile, shutil
        for tool in ["scrot", "import", "grim"]:
            if shutil.which(tool):
                try:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        tmp_path = f.name
                    if tool == "scrot":
                        subprocess.run(["scrot", tmp_path], capture_output=True, timeout=5)
                    elif tool == "import":
                        subprocess.run(["import", "-window", "root", tmp_path], capture_output=True, timeout=5)
                    elif tool == "grim":
                        subprocess.run(["grim", tmp_path], capture_output=True, timeout=5)
                    
                    data = Path(tmp_path).read_bytes()
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                    if data:
                        return data
                except Exception:
                    pass

    return b""


# ── Random / user data ─────────────────────────────────────────────────────────

_FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Blake", "Avery"]
_LAST  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
_DOMS  = ["gmail.com", "yahoo.com", "outlook.com", "proton.me"]


def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()
    if dt == "name":
        return f"{random.choice(_FIRST)} {random.choice(_LAST)}"
    if dt == "first_name":
        return random.choice(_FIRST)
    if dt == "last_name":
        return random.choice(_LAST)
    if dt == "email":
        f = random.choice(_FIRST).lower()
        l = random.choice(_LAST).lower()
        n = random.randint(10, 999)
        return f"{f}.{l}{n}@{random.choice(_DOMS)}"
    if dt == "username":
        return f"{random.choice(_FIRST).lower()}{random.randint(100, 9999)}"
    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))
    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"
    if dt == "birthday":
        return f"{random.randint(1,12):02d}/{random.randint(1,28):02d}/{random.randint(1980,2002)}"
    if dt == "address":
        streets = ["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"]
        return f"{random.randint(100, 9999)} {random.choice(streets)}"
    if dt == "zip":
        return str(random.randint(10000, 99999))
    return f"random_{dt}_{random.randint(1000,9999)}"


def _user_profile() -> dict:
    try:
        if _MEMORY_PATH.exists():
            data     = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            return {k: v.get("value", "") for k, v in identity.items()}
    except Exception:
        pass
    return {}


# ── Safe screenshot path ───────────────────────────────────────────────────────

def _safe_ss_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "jarvis_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(requested).expanduser().resolve()
        if p.is_relative_to(Path.home().resolve()):
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
    except Exception:
        pass
    return fallback


# ── Core input functions ───────────────────────────────────────────────────────

def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("pyautogui not installed. Run: pip install pyautogui")


def _type_text(text: str, interval: float = 0.03) -> str:
    if _PYAUTOGUI:
        try:
            time.sleep(0.1)
            pyautogui.typewrite(text, interval=interval)
            return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"
        except Exception:
            pass
    if _OS == "Linux" and __import__("shutil").which("xdotool"):
        try:
            subprocess.run(["xdotool", "type", text], capture_output=True, timeout=5)
            return f"Typed via xdotool: {text[:60]}"
        except Exception:
            pass
    return f"Unable to type text: {text[:30]}"


def _smart_type(text: str, clear_first: bool = True) -> str:
    if clear_first:
        _clear_field()
        time.sleep(0.08)
    if _PYPERCLIP:
        try:
            pyperclip.copy(text)
            time.sleep(0.08)
            return _hotkey("ctrl", "v")
        except Exception:
            pass
    return _type_text(text, interval=0.03)


def _click(x=None, y=None, button: str = "left", clicks: int = 1, interval: float = 0.0) -> str:
    if _PYAUTOGUI:
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button, clicks=clicks, interval=interval)
                return f"{'Double-c' if clicks == 2 else 'C'}licked ({x},{y}) [{button}]"
            pyautogui.click(button=button, clicks=clicks)
            return f"Clicked at current position [{button}]"
        except Exception:
            pass
    
    # xdotool fallback for Linux
    if _OS == "Linux" and __import__("shutil").which("xdotool"):
        try:
            btn_map = {"left": "1", "middle": "2", "right": "3"}
            b = btn_map.get(button, "1")
            if x is not None and y is not None:
                subprocess.run(["xdotool", "mousemove", str(x), str(y)], capture_output=True, timeout=5)
            for _ in range(clicks):
                subprocess.run(["xdotool", "click", b], capture_output=True, timeout=5)
            return f"Clicked ({x},{y}) via xdotool [{button}]"
        except Exception:
            pass

    return f"Click failed: ({x},{y})"
    return f"Clicked at current position [{button}]"


def _right_click(x=None, y=None) -> str:
    return _click(x, y, button="right")


def _double_click(x=None, y=None) -> str:
    return _click(x, y, clicks=2)


def _triple_click(x=None, y=None) -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(x, y, clicks=3, interval=0.08)
    else:
        pyautogui.click(clicks=3, interval=0.08)
    return f"Triple-clicked ({x},{y})"


def _hotkey(*keys) -> str:
    _require_pyautogui()
    pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"


def _press(key: str) -> str:
    _require_pyautogui()
    pyautogui.press(key)
    return f"Pressed: {key}"


def _key_down(key: str) -> str:
    _require_pyautogui()
    pyautogui.keyDown(key)
    return f"Key down: {key}"


def _key_up(key: str) -> str:
    _require_pyautogui()
    pyautogui.keyUp(key)
    return f"Key up: {key}"


def _scroll(direction: str = "down", amount: int = 3) -> str:
    _require_pyautogui()
    vertical = direction in ("up", "down")
    clicks   = amount if direction in ("up", "right") else -amount
    if vertical:
        pyautogui.scroll(clicks)
    else:
        pyautogui.hscroll(clicks)
    return f"Scrolled {direction} ×{amount}"


def _move(x: int, y: int, duration: float = 0.25) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x, y, duration=duration)
    return f"Mouse → ({x},{y})"


def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.45) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x1, y1, duration=0.15)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    return f"Dragged ({x1},{y1}) → ({x2},{y2})"


def _drag_rel(dx: int, dy: int, duration: float = 0.35) -> str:
    _require_pyautogui()
    pyautogui.drag(dx, dy, duration=duration, button="left")
    return f"Dragged relative ({dx},{dy})"


def _get_mouse_pos() -> str:
    _require_pyautogui()
    pos = pyautogui.position()
    return f"({pos.x},{pos.y})"


def _clipboard_get() -> str:
    return get_clipboard_text()


def _clipboard_set(text: str) -> str:
    success = set_clipboard_text(text)
    if success:
        return f"Clipboard: {text[:60]}{'…' if len(text) > 60 else ''}"
    return "Failed to write to clipboard"


def _copy_selection() -> str:
    if _OS == "Darwin":
        _hotkey("command", "c")
    else:
        _hotkey("ctrl", "c")
    time.sleep(0.15)
    clip_text = get_clipboard_text()
    if clip_text:
        return f"Copied to clipboard: {clip_text[:60]}{'…' if len(clip_text) > 60 else ''}"
    return "(copied)"


def _screenshot(save_path: str | None = None) -> str:
    _require_pyautogui()
    path = _safe_ss_path(save_path)
    img  = pyautogui.screenshot()
    img.save(str(path))
    return f"Screenshot saved: {path}"


def _clear_field() -> str:
    _require_pyautogui()
    if _OS == "Darwin":
        pyautogui.hotkey("command", "a")
    else:
        pyautogui.hotkey("ctrl", "a")
    time.sleep(0.06)
    pyautogui.press("delete")
    return "Field cleared"


def _select_all() -> str:
    _require_pyautogui()
    if _OS == "Darwin":
        pyautogui.hotkey("command", "a")
    else:
        pyautogui.hotkey("ctrl", "a")
    return "Selected all"


# ── Window management ─────────────────────────────────────────────────────────

def _focus_window(title: str) -> str:
    if _OS == "Windows":
        try:
            script = f'(New-Object -ComObject WScript.Shell).AppActivate("{title}")'
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, timeout=5
            )
            time.sleep(0.25)
            return f"Focused: {title}"
        except Exception as e:
            return f"focus_window Windows error: {e}"

    if _OS == "Darwin":
        script = (f'tell application "System Events" to '
                  f'set frontmost of (first process whose name contains "{title}") to true')
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            time.sleep(0.25)
            return f"Focused: {title}"
        except Exception as e:
            return f"focus_window macOS error: {e}"

    # Linux
    for cmd in [["wmctrl", "-a", title], ["xdotool", "search", "--name", title, "windowactivate"]]:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                time.sleep(0.2)
                return f"Focused: {title}"
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return f"Could not focus: {title}"


def _get_active_window() -> str:
    if _PYGW:
        try:
            w = gw.getActiveWindow()
            if w:
                return f"Active window: '{w.title}' at ({w.left},{w.top}) size {w.width}×{w.height}"
        except Exception:
            pass
    return "Active window info unavailable"


def _list_windows() -> str:
    if _PYGW:
        try:
            wins = gw.getAllWindows()
            lines = [f"  [{i}] {w.title}" for i, w in enumerate(wins) if w.title]
            return "Windows:\n" + "\n".join(lines[:20])
        except Exception:
            pass
    return "Window list unavailable"


def _minimize_window() -> str:
    _require_pyautogui()
    if _OS == "Darwin":
        pyautogui.hotkey("command", "m")
    else:
        pyautogui.hotkey("win", "down")
    return "Window minimized"


def _maximize_window() -> str:
    _require_pyautogui()
    if _OS == "Darwin":
        pyautogui.hotkey("ctrl", "command", "f")
    elif _OS == "Windows":
        pyautogui.hotkey("win", "up")
    else:
        subprocess.run(
            ["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"],
            capture_output=True
        )
    return "Window maximized"


def _close_window() -> str:
    _require_pyautogui()
    if _OS == "Darwin":
        pyautogui.hotkey("command", "w")
    else:
        pyautogui.hotkey("alt", "F4")
    return "Window closed"


def _snap_left() -> str:
    _require_pyautogui()
    if _OS == "Windows":
        pyautogui.hotkey("win", "left")
    elif _OS == "Darwin":
        pass  # macOS uses Rectangle/BetterSnap etc.
    return "Window snapped left"


def _snap_right() -> str:
    _require_pyautogui()
    if _OS == "Windows":
        pyautogui.hotkey("win", "right")
    return "Window snapped right"


# ── AI-powered screen element finder ─────────────────────────────────────────

_find_cache: dict[str, tuple[int, int, float]] = {}  # description → (x, y, timestamp)
_find_lock  = threading.Lock()


def _screen_find(description: str, use_cache: bool = True) -> tuple[int, int] | None:
    """Use Gemini vision to find a UI element on screen."""
    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] ⚠ No API key for screen_find")
        return None

    # Check cache (5-second TTL)
    if use_cache:
        with _find_lock:
            cached = _find_cache.get(description)
            if cached and (time.time() - cached[2]) < 5.0:
                print(f"[ComputerControl] ⚡ Cache hit for: {description}")
                return (cached[0], cached[1])

def _call_vision_llm(img_bytes: bytes, prompt: str, mime_type: str = "image/png") -> str:
    """Resilient Vision LLM caller via local gateway or fallback cloud."""
    import base64
    import urllib.request
    import json
    import io as _io

    # Optimize & compress image bytes for sub-second vision inference
    try:
        if _PIL:
            img = PILImage.open(_io.BytesIO(img_bytes)).convert("RGB")
            img.thumbnail((1280, 720), PILImage.BILINEAR)
            buf = _io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            img_bytes = buf.getvalue()
            mime_type = "image/jpeg"
    except Exception:
        pass

    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    # 1. Try local gateway models (unlimited quota)
    for model_name in ["gemini-3.1-flash-image", "gemini-3-pro-image", "gemini-3-flash"]:
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}}
                        ]
                    }
                ]
            }
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:8045/v1/chat/completions",
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer sk-5ec70bf9fa324084b7a7326babf52c45"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                content = body.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if content:
                    return content
        except Exception:
            continue

    # 2. Fallback to Google GenAI Cloud SDK if local gateway is unreachable
    try:
        api_key = _get_api_key()
        if api_key:
            from google import genai
            from google.genai import types as gtypes
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-3.1-flash-image",
                contents=[
                    gtypes.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                    prompt,
                ],
            )
            if response and response.text:
                return response.text.strip()
    except Exception as cloud_err:
        return f"Vision LLM unavailable: {cloud_err}"

    return "Could not generate vision description from current screen."


def screen_find(description: str) -> tuple[int, int] | None:
    """Find a UI element on screen using Gemini vision."""
    # Check cache
    with _find_lock:
        if description in _find_cache:
            cached = _find_cache[description]
            if time.time() - cached[2] < 10.0:  # 10s TTL
                print(f"[ComputerControl] [CACHE] Cache hit for: {description}")
                return (cached[0], cached[1])

    try:
        w, h = _screen_size()
        img_bytes = _take_screenshot_bytes()
        if not img_bytes:
            return None

        prompt = (
            f"This is a screenshot of a {w}×{h} screen. "
            f"Find the UI element described as: '{description}'. "
            f"Reply with ONLY the center pixel coordinates as: x,y "
            f"If not visible, reply: NOT_FOUND"
        )

        text = _call_vision_llm(img_bytes, prompt)
        if "NOT_FOUND" in text.upper():
            return None

        match = re.search(r"(\d+)\s*,\s*(\d+)", text)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            with _find_lock:
                _find_cache[description] = (x, y, time.time())
            return (x, y)

    except Exception as e:
        print(f"[ComputerControl] [ERROR] screen_find: {e}")

    return None


def _screen_read(region: tuple | None = None) -> str:
    """Read text from screen using OCR (Gemini vision)."""
    try:
        img_bytes = _take_screenshot_bytes()
        if not img_bytes:
            return "Could not capture screen."

        return _call_vision_llm(img_bytes, "Read all visible text on the screen. Return a clean, organized transcript.")
    except Exception as e:
        return f"OCR error: {e}"


def _screen_describe() -> str:
    """Get a description of what's currently on screen."""
    try:
        img_bytes = _take_screenshot_bytes()
        if not img_bytes:
            return "Could not capture screen."

        return _call_vision_llm(img_bytes, "Describe what is currently visible on this screen in 2-3 sentences. Be specific about open apps, windows, and content.")
    except Exception as e:
        return f"Screen describe error: {e}"
        return f"Screen describe error: {e}"


def _wait_for_element(description: str, timeout: float = 15.0) -> str:
    """Wait until a UI element appears on screen."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        coords = _screen_find(description, use_cache=False)
        if coords:
            return f"Element found at ({coords[0]},{coords[1]}): {description}"
        time.sleep(1.0)
    return f"Timeout: element not found: {description}"


def _smart_click_elem(description: str) -> str:
    """AI-powered smart click: find and click by description."""
    if not _PYAUTOGUI:
        return "pyautogui not installed."
    coords = _screen_find(description)
    if coords:
        time.sleep(0.15)
        _click(coords[0], coords[1])
        return f"Clicked '{description}' at ({coords[0]},{coords[1]})"
    return f"Element not found: '{description}'"


def _smart_type_elem(description: str, text: str) -> str:
    """Find an input field by description and type into it."""
    if not _PYAUTOGUI:
        return "pyautogui not installed."
    coords = _screen_find(description)
    if coords:
        _click(coords[0], coords[1])
        time.sleep(0.12)
        _clear_field()
        time.sleep(0.06)
        _smart_type(text, clear_first=False)
        return f"Typed into '{description}'"
    return f"Input field not found: '{description}'"


# ── Main entry point ──────────────────────────────────────────────────────────

def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Full computer control for JARVIS MK37.

    Actions:
      Mouse:    move, click, double_click, triple_click, right_click,
                drag, drag_rel, scroll, get_pos
      Keyboard: type, smart_type, hotkey, press, key_down, key_up,
                clear_field, select_all
      Clipboard:copy, paste, clipboard_get, clipboard_set
      Screen:   screenshot, screen_find, screen_click, smart_click,
                smart_type_elem, screen_read, screen_describe,
                wait_for_element
      Windows:  focus_window, get_active_window, list_windows,
                minimize, maximize, close_window, snap_left, snap_right
      Data:     random_data, user_data
      Util:     wait
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified."

    if player:
        player.write_log(f"[Computer] {action}")

    print(f"[ComputerControl] [ACTION] {action}  {params}")

    try:
        # ── Mouse ─────────────────────────────────────────────────────────
        if action in ("move",):
            return _move(int(params.get("x", 0)), int(params.get("y", 0)),
                         float(params.get("duration", 0.25)))

        if action in ("click", "left_click"):
            return _click(params.get("x"), params.get("y"), "left", 1)

        if action in ("double_click",):
            return _double_click(params.get("x"), params.get("y"))

        if action in ("triple_click",):
            return _triple_click(params.get("x"), params.get("y"))

        if action in ("right_click",):
            return _right_click(params.get("x"), params.get("y"))

        if action in ("drag",):
            return _drag(
                int(params.get("x1", 0)), int(params.get("y1", 0)),
                int(params.get("x2", 0)), int(params.get("y2", 0)),
                float(params.get("duration", 0.45)),
            )

        if action in ("drag_rel", "drag_relative"):
            return _drag_rel(int(params.get("dx", 0)), int(params.get("dy", 0)))

        if action in ("scroll",):
            return _scroll(
                direction=params.get("direction", "down"),
                amount=int(params.get("amount", 3)),
            )

        if action in ("get_pos", "mouse_pos"):
            return _get_mouse_pos()

        # ── Keyboard ──────────────────────────────────────────────────────
        if action in ("type",):
            return _type_text(params.get("text", ""),
                              float(params.get("interval", 0.03)))

        if action in ("smart_type",):
            return _smart_type(
                params.get("text", ""),
                bool(params.get("clear_first", True)),
            )

        if action in ("hotkey",):
            raw  = params.get("keys", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return _hotkey(*keys)

        if action in ("press",):
            return _press(params.get("key", "enter"))

        if action in ("key_down",):
            return _key_down(params.get("key", ""))

        if action in ("key_up",):
            return _key_up(params.get("key", ""))

        if action in ("clear_field",):
            return _clear_field()

        if action in ("select_all",):
            return _select_all()

        # ── Clipboard ──────────────────────────────────────────────────────
        if action in ("clipboard_get", "read_clipboard"):
            return _clipboard_get()

        if action in ("copy",):
            return _copy_selection()

        if action in ("paste", "clipboard_set"):
            text = params.get("text", "")
            result = _clipboard_set(text)
            if action == "paste":
                time.sleep(0.05)
                _require_pyautogui()
                if _OS == "Darwin":
                    pyautogui.hotkey("command", "v")
                else:
                    pyautogui.hotkey("ctrl", "v")
                return f"Pasted: {text[:60]}{'…' if len(text) > 60 else ''}"
            return result

        # ── Screen ─────────────────────────────────────────────────────────
        if action in ("screenshot",):
            return _screenshot(params.get("path"))

        if action in ("screen_find",):
            coords = _screen_find(
                params.get("description", ""),
                bool(params.get("use_cache", True)),
            )
            return f"{coords[0]},{coords[1]}" if coords else "NOT_FOUND"

        if action in ("screen_click",):
            return _smart_click_elem(params.get("description", ""))

        if action in ("smart_click",):
            desc = params.get("description", "")
            # Try AI first, fallback to pyautogui role-based search
            coords = _screen_find(desc)
            if coords:
                time.sleep(0.12)
                _click(coords[0], coords[1])
                return f"Smart-clicked '{desc}' at ({coords[0]},{coords[1]})"
            # Fallback: get_by_text style (placeholder)
            return f"Element not found: '{desc}'"

        if action in ("smart_type_elem", "smart_type_into"):
            return _smart_type_elem(
                params.get("description", ""),
                params.get("text", ""),
            )

        if action in ("screen_read", "ocr"):
            return _screen_read()

        if action in ("screen_describe",):
            return _screen_describe()

        if action in ("wait_for_element",):
            return _wait_for_element(
                params.get("description", ""),
                float(params.get("timeout", 15.0)),
            )

        # ── Windows ────────────────────────────────────────────────────────
        if action in ("focus_window",):
            return _focus_window(params.get("title", ""))

        if action in ("get_active_window", "active_window"):
            return _get_active_window()

        if action in ("list_windows",):
            return _list_windows()

        if action in ("minimize",):
            return _minimize_window()

        if action in ("maximize",):
            return _maximize_window()

        if action in ("close_window",):
            return _close_window()

        if action in ("snap_left",):
            return _snap_left()

        if action in ("snap_right",):
            return _snap_right()

        # ── Data ────────────────────────────────────────────────────────────
        if action in ("random_data",):
            dt     = params.get("type", "name")
            result = _random_data(dt)
            print(f"[ComputerControl] 🎲 random {dt} → {result}")
            return result

        if action in ("user_data",):
            field   = params.get("field", "name")
            profile = _user_profile()
            value   = profile.get(field, "")
            if not value:
                value = _random_data(field)
                print(f"[ComputerControl] ⚠ No '{field}' in memory, using random: {value}")
            return value

        # ── Utility ─────────────────────────────────────────────────────────
        if action in ("wait", "sleep"):
            secs = float(params.get("seconds", 1.0))
            secs = min(secs, 60.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        if action in ("screen_size",):
            w, h = _screen_size()
            return f"Screen: {w}×{h}"

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] [ERROR] {action}: {e}")
        return f"computer_control '{action}' failed: {e}"
