import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from datetime import datetime

logger = logging.getLogger("JARVIS.Actions.Desktop")

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


def _get_base_dir() -> Path:
    from brjarvis.core.paths import paths
    return paths.PROJECT_ROOT

def _get_api_key() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]
    
def _get_desktop() -> Path:
    if _OS == "Linux":
        xdg = os.environ.get("XDG_DESKTOP_DIR", "")
        if xdg and Path(xdg).exists():
            return Path(xdg)
    return Path.home() / "Desktop"

def _build_sandbox() -> dict:
    import time

    safe_builtins = {
        "print": print,
        "len": len, "str": str, "int": int, "float": float,
        "bool": bool, "list": list, "dict": dict, "tuple": tuple,
        "range": range, "enumerate": enumerate, "sorted": sorted,
        "isinstance": isinstance, "hasattr": hasattr, "getattr": getattr,
        "max": max, "min": min, "sum": sum, "abs": abs,
        "zip": zip, "map": map, "filter": filter,
    }

    sandbox = {
        "__builtins__": safe_builtins,
        "Path": Path,
        "time": time,
        "shutil": type("shutil", (), {
            "copy2":      shutil.copy2,
            "copytree":   shutil.copytree,
            "disk_usage": shutil.disk_usage,
        })(),
        "os_path": os.path,  
    }

    if _PYAUTOGUI:
        class PyAutoGUIWrapper:
            def __init__(self, original):
                self._original = original
                try:
                    self._screen_width, self._screen_height = original.size()
                except Exception:
                    self._screen_width, self._screen_height = 1920, 1080
                self._ref_width = 1920
                self._ref_height = 1080

            def _scale(self, x, y):
                if x is None or y is None:
                    return x, y
                scaled_x = int((x / self._ref_width) * self._screen_width)
                scaled_y = int((y / self._ref_height) * self._screen_height)
                return scaled_x, scaled_y

            def click(self, x=None, y=None, *args, **kwargs):
                if x is not None and y is not None and not isinstance(x, str):
                    x, y = self._scale(x, y)
                return self._original.click(x, y, *args, **kwargs)

            def moveTo(self, x=None, y=None, *args, **kwargs):
                if x is not None and y is not None:
                    x, y = self._scale(x, y)
                return self._original.moveTo(x, y, *args, **kwargs)

            def dragTo(self, x=None, y=None, *args, **kwargs):
                if x is not None and y is not None:
                    x, y = self._scale(x, y)
                return self._original.dragTo(x, y, *args, **kwargs)

            def mouseDown(self, x=None, y=None, *args, **kwargs):
                if x is not None and y is not None:
                    x, y = self._scale(x, y)
                return self._original.mouseDown(x, y, *args, **kwargs)

            def mouseUp(self, x=None, y=None, *args, **kwargs):
                if x is not None and y is not None:
                    x, y = self._scale(x, y)
                return self._original.mouseUp(x, y, *args, **kwargs)

            def doubleClick(self, x=None, y=None, *args, **kwargs):
                if x is not None and y is not None:
                    x, y = self._scale(x, y)
                return self._original.doubleClick(x, y, *args, **kwargs)

            def rightClick(self, x=None, y=None, *args, **kwargs):
                if x is not None and y is not None:
                    x, y = self._scale(x, y)
                return self._original.rightClick(x, y, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._original, name)

        sandbox["pyautogui"] = PyAutoGUIWrapper(pyautogui)

        def wait_for_element(image_path: str, timeout: float = 5.0):
            import time
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                try:
                    pos = pyautogui.locateOnScreen(image_path, confidence=0.8)
                    if pos is not None:
                        return pos
                except Exception:
                    pass
                time.sleep(0.2)
            raise TimeoutError(f"Element '{image_path}' not found on screen within {timeout}s")

        sandbox["wait_for_element"] = wait_for_element


    if _OS == "Windows":
        try:
            import ctypes
            import winreg
            sandbox["ctypes"] = ctypes
            sandbox["winreg"] = type("winreg", (), {
                # Sadece okuma
                "OpenKey":      winreg.OpenKey,
                "QueryValueEx": winreg.QueryValueEx,
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            })()
        except ImportError:
            pass

    return sandbox


import ast


def _is_ast_safe(code: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return False, f"Forbidden attribute access: {node.attr}"
            if isinstance(node, ast.Name) and node.id in ("eval", "exec", "__import__", "breakpoint"):
                return False, f"Forbidden builtin: {node.id}"
        return True, ""
    except SyntaxError as se:
        return False, f"Syntax error: {se}"


def _safe_ast_execute(code: str, scope: dict) -> dict:
    """Safely interpret whitelisted AST statements in sandbox scope without exec()."""
    tree = ast.parse(code)

    def _eval_expr(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id in scope:
                return scope[node.id]
            builtins_dict = scope.get("__builtins__", {})
            if isinstance(builtins_dict, dict) and node.id in builtins_dict:
                return builtins_dict[node.id]
            elif node.id in ("True", "False", "None"):
                return {"True": True, "False": False, "None": None}[node.id]
            raise ValueError(f"Undefined symbol in AST: {node.id}")
        elif isinstance(node, ast.Attribute):
            val = _eval_expr(node.value)
            if node.attr.startswith("__"):
                raise PermissionError(f"Forbidden attribute access: {node.attr}")
            return getattr(val, node.attr)
        elif isinstance(node, ast.Call):
            func = _eval_expr(node.func)
            args = [_eval_expr(a) for a in node.args]
            kwargs = {k.arg: _eval_expr(k.value) for k in node.keywords if k.arg is not None}
            if not callable(func):
                raise TypeError(f"Target object is not callable: {func}")
            return func(*args, **kwargs)
        elif isinstance(node, ast.List):
            return [_eval_expr(e) for e in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(_eval_expr(e) for e in node.elts)
        elif isinstance(node, ast.Dict):
            return {_eval_expr(k): _eval_expr(v) for k, v in zip(node.keys, node.values)}
        elif isinstance(node, ast.BinOp):
            left = _eval_expr(node.left)
            right = _eval_expr(node.right)
            if isinstance(node.op, ast.Add): return left + right
            elif isinstance(node.op, ast.Sub): return left - right
            elif isinstance(node.op, ast.Mult): return left * right
            elif isinstance(node.op, ast.Div): return left / right
            elif isinstance(node.op, ast.Mod): return left % right
            else: raise NotImplementedError(f"Unsupported binary op: {node.op}")
        elif isinstance(node, ast.UnaryOp):
            operand = _eval_expr(node.operand)
            if isinstance(node.op, ast.USub): return -operand
            elif isinstance(node.op, ast.Not): return not operand
            else: raise NotImplementedError(f"Unsupported unary op: {node.op}")
        elif isinstance(node, ast.Subscript):
            val = _eval_expr(node.value)
            idx = _eval_expr(node.slice)
            return val[idx]
        else:
            raise NotImplementedError(f"Unsupported AST expression: {type(node).__name__}")

    def _exec_stmt(stmt: ast.AST):
        if isinstance(stmt, ast.Expr):
            _eval_expr(stmt.value)
        elif isinstance(stmt, ast.Assign):
            val = _eval_expr(stmt.value)
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    scope[target.id] = val
        elif isinstance(stmt, ast.FunctionDef):
            def _fn(*fn_args, **fn_kwargs):
                for param, arg in zip([a.arg for a in stmt.args.args], fn_args):
                    scope[param] = arg
                for body_stmt in stmt.body:
                    _exec_stmt(body_stmt)
            scope[stmt.name] = _fn
        elif isinstance(stmt, ast.For):
            iter_val = _eval_expr(stmt.iter)
            if isinstance(stmt.target, ast.Name):
                for item in iter_val:
                    scope[stmt.target.id] = item
                    for body_stmt in stmt.body:
                        _exec_stmt(body_stmt)
        elif isinstance(stmt, ast.If):
            test_val = _eval_expr(stmt.test)
            branch = stmt.body if test_val else stmt.orelse
            for body_stmt in branch:
                _exec_stmt(body_stmt)
        elif isinstance(stmt, ast.Pass):
            pass
        else:
            raise NotImplementedError(f"Unsupported AST statement: {type(stmt).__name__}")

    for stmt in tree.body:
        _exec_stmt(stmt)

    return scope


def _execute_generated_code(code: str, player=None) -> str:
    if not code or code.strip() == "UNSAFE":
        return "This action cannot be performed safely."

    # Kod temizleme
    if code.startswith("```"):
        lines = code.split("\n")
        code  = "\n".join(lines[1:-1]).strip()

    is_safe, reason = _is_ast_safe(code)
    if not is_safe:
        logger.warning("Security blocked execution: %s", reason)
        return f"⚠️ Security Block: {reason}"

    try:
        scope: dict = _build_sandbox()
        # Ensure builtins in scope are strictly restricted
        scope["__builtins__"] = {
            "range": range, "len": len, "str": str, "int": int, "float": float,
            "bool": bool, "list": list, "dict": dict, "tuple": tuple, "set": set,
            "print": print, "min": min, "max": max, "sum": sum, "abs": abs
        }
        _safe_ast_execute(code, scope)
        fn = scope.get("run_desktop_task")
        if callable(fn):
            res = fn()
            return str(res) if res is not None else "Task executed successfully."
        return "Script executed."
    except Exception as e:
        logger.error("Exec error: %s\nCode:\n%s", e, code[:300])
        return f"Execution error: {e}"


def _ask_gemini_for_desktop_action(task: str) -> str:

    from actions._gemini_client import get_gemini_client as _get_gc, get_proxy_model as _gpm
    _client = _get_gc()
    _desktop_model = _gpm("gemini-3.5-flash", "gemini-2.5-flash")

    desktop = str(_get_desktop())

    os_specific = ""
    if _OS == "Windows":
        os_specific = "- ctypes (Windows API calls, read-only)\n- winreg (registry READ only)"
    elif _OS == "Darwin":
        os_specific = "- subprocess is NOT available; use pyautogui or Path only"
    else:
        os_specific = "- subprocess is NOT available; use pyautogui or Path only"

    prompt = f"""You are a desktop automation assistant.
Current OS: {_OS}
Desktop path: {desktop}

Generate safe Python code to accomplish the task below.
Allowed modules ONLY:
- pyautogui (mouse, keyboard — if needed)
- pathlib.Path (file/folder inspection only, no deletion)
- shutil.copy2, shutil.copytree, shutil.disk_usage (NO move, NO rmtree)
- os_path (os.path equivalent, read-only)
- time.sleep
{os_specific}

Hard rules:
- NO file deletion (no unlink, no rmtree, no remove)
- NO subprocess calls
- NO exec() or eval() inside the code
- NO import statements (modules are pre-injected)
- NO file write operations except explicitly requested
- If task cannot be done safely with these tools, output exactly: UNSAFE

Output ONLY the Python code. No explanation, no markdown, no backticks.

Task: {task}"""

    try:
        response = _client.models.generate_content(model=_desktop_model, contents=prompt)
        code = response.text.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            code  = "\n".join(lines[1:-1]).strip()
        return code
    except Exception as e:
        return f"ERROR: {e}"

def set_wallpaper(image_path: str) -> str:
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        return f"Image not found: {image_path}"
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        return f"Unsupported format: {path.suffix}. Use jpg, png, bmp or webp."

    try:
        if _OS == "Windows":
            import ctypes
            if path.suffix.lower() in {".webp", ".png"}:
                try:
                    from PIL import Image  # type: ignore
                    bmp_path = Path(tempfile.mktemp(suffix=".bmp"))
                    Image.open(path).convert("RGB").save(bmp_path, "BMP")
                    path = bmp_path
                except ImportError:
                    pass 
            ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3)
            return f"Wallpaper set: {path.name}"

        elif _OS == "Darwin":
            script = (
                f'tell application "System Events" to tell every desktop to '
                f'set picture to POSIX file "{path}"'
            )
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return f"Wallpaper set: {path.name}"

        else:
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            uri = f"file://{path}"

            if "gnome" in desktop_env or "unity" in desktop_env:
                subprocess.run([
                    "gsettings", "set", "org.gnome.desktop.background",
                    "picture-uri", uri
                ], capture_output=True)
                subprocess.run([
                    "gsettings", "set", "org.gnome.desktop.background",
                    "picture-uri-dark", uri
                ], capture_output=True)

            elif "kde" in desktop_env:
                # KDE Plasma
                script = f"""
var allDesktops = desktops();
for (var i = 0; i < allDesktops.length; i++) {{
    d = allDesktops[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file://{path}");
}}
"""
                subprocess.run(
                    ["qdbus", "org.kde.plasmashell", "/PlasmaShell",
                     "org.kde.PlasmaShell.evaluateScript", script],
                    capture_output=True
                )

            elif "xfce" in desktop_env:
                subprocess.run([
                    "xfconf-query", "-c", "xfce4-desktop",
                    "-p", "/backdrop/screen0/monitor0/workspace0/last-image",
                    "-s", str(path)
                ], capture_output=True)

            else:
                result = subprocess.run(
                    ["feh", "--bg-scale", str(path)],
                    capture_output=True
                )
                if result.returncode != 0:
                    return (
                        f"Could not set wallpaper automatically on {desktop_env}. "
                        f"Try manually or install 'feh'."
                    )

            return f"Wallpaper set: {path.name}"

    except Exception as e:
        return f"Could not set wallpaper: {e}"


def set_wallpaper_from_url(url: str) -> str:
    try:
        import urllib.request
        suffix = Path(url.split("?")[0]).suffix or ".jpg"
        tmp    = Path(tempfile.mktemp(suffix=suffix))
        urllib.request.urlretrieve(url, str(tmp))
        result = set_wallpaper(str(tmp))
        try:
            tmp.unlink()
        except Exception:
            pass
        return result
    except Exception as e:
        return f"Could not download wallpaper: {e}"


def get_current_wallpaper() -> str:
    try:
        if _OS == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop"
            )
            val, _ = winreg.QueryValueEx(key, "Wallpaper")
            winreg.CloseKey(key)
            return f"Current wallpaper: {val}"

        elif _OS == "Darwin":
            script = (
                'tell application "System Events" to get picture of desktop 1'
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True
            )
            return f"Current wallpaper: {result.stdout.strip()}"

        else:
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
            if "gnome" in desktop_env or "unity" in desktop_env:
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                    capture_output=True, text=True
                )
                return f"Current wallpaper: {result.stdout.strip()}"
            return "Wallpaper path retrieval not supported for this desktop environment."

    except Exception as e:
        return f"Could not get wallpaper: {e}"

FILE_TYPE_MAP = {
    "Images":      {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
    "Documents":   {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx",
                    ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
    "Videos":      {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Music":       {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives":    {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code":        {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
                    ".cpp", ".java", ".cs", ".go", ".rs", ".sh", ".php"},
    "Executables": {".exe", ".msi", ".bat", ".cmd", ".sh", ".appimage", ".deb", ".rpm"},
}

_SKIP_EXTENSIONS = {
    "Windows": {".lnk", ".url"},
    "Darwin":  {".webloc"},
    "Linux":   {".desktop"},
}


def organize_desktop(mode: str = "by_type") -> str:
    desktop       = _get_desktop()
    skip_exts     = _SKIP_EXTENSIONS.get(_OS, set())
    moved, skipped = [], []

    for item in desktop.iterdir():
        if item.is_dir() or item.name.startswith("."):
            continue
        if item.suffix.lower() in skip_exts:
            continue

        if mode == "by_date":
            mtime       = datetime.fromtimestamp(item.stat().st_mtime)
            folder_name = mtime.strftime("%Y-%m")
        else:
            ext         = item.suffix.lower()
            folder_name = "Others"
            for folder, exts in FILE_TYPE_MAP.items():
                if ext in exts:
                    folder_name = folder
                    break

        target_dir = desktop / folder_name
        target_dir.mkdir(exist_ok=True)
        new_path = target_dir / item.name

        if new_path.exists():
            skipped.append(item.name)
            continue

        shutil.move(str(item), str(new_path))
        moved.append(f"{item.name} → {folder_name}/")

    result = f"Desktop organized ({mode}): {len(moved)} files moved."
    if moved:
        result += "\n" + "\n".join(moved[:8])
        if len(moved) > 8:
            result += f"\n... and {len(moved) - 8} more."
    if skipped:
        result += f"\n{len(skipped)} file(s) skipped (name conflict)."
    return result


def list_desktop() -> str:
    desktop = _get_desktop()
    items   = []
    for item in sorted(desktop.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            try:
                count = len(list(item.iterdir()))
            except PermissionError:
                count = "?"
            items.append(f"📁 {item.name}/ ({count} items)")
        else:
            size     = item.stat().st_size
            size_str = (
                f"{size / 1024:.1f} KB" if size < 1024 * 1024
                else f"{size / 1024 / 1024:.1f} MB"
            )
            items.append(f"📄 {item.name} ({size_str})")

    if not items:
        return "Desktop is empty."
    return f"Desktop ({len(items)} items):\n" + "\n".join(items)


def clean_desktop() -> str:
    desktop     = _get_desktop()
    skip_exts   = _SKIP_EXTENSIONS.get(_OS, set())
    today       = datetime.now().strftime("%Y-%m-%d")
    archive_dir = desktop / f"Desktop Archive {today}"
    archive_dir.mkdir(exist_ok=True)

    moved = 0
    for item in desktop.iterdir():
        if item.is_dir() or item.name.startswith("."):
            continue
        if item.suffix.lower() in skip_exts:
            continue
        new_path = archive_dir / item.name
        if not new_path.exists():
            shutil.move(str(item), str(new_path))
            moved += 1

    return f"Desktop cleaned: {moved} files archived to '{archive_dir.name}'."


def get_desktop_stats() -> str:
    desktop    = _get_desktop()
    files      = [i for i in desktop.iterdir() if i.is_file()]
    folders    = [i for i in desktop.iterdir() if i.is_dir()]
    total_size = sum(f.stat().st_size for f in files if f.exists())
    size_str   = (
        f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024
        else f"{total_size / 1024 / 1024:.1f} MB"
    )
    return (
        f"Desktop stats ({_OS}):\n"
        f"  Files   : {len(files)}\n"
        f"  Folders : {len(folders)}\n"
        f"  Size    : {size_str}\n"
        f"  Path    : {desktop}"
    )

def desktop_control(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    parameters:
        action : wallpaper | wallpaper_url | current_wallpaper |
                 organize  | clean | list | stats |
                 task (AI-powered)
        path   : image path for 'wallpaper'
        url    : image URL for 'wallpaper_url'
        mode   : 'by_type' or 'by_date' for 'organize'
        task   : natural language description for AI-powered actions
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    task   = params.get("task", "").strip()

    if player:
        player.write_log(f"[desktop] {action or task[:40]}")

    try:
        if action == "wallpaper":
            path = params.get("path", "")
            return set_wallpaper(path) if path else "No image path provided."

        elif action == "wallpaper_url":
            url = params.get("url", "")
            return set_wallpaper_from_url(url) if url else "No URL provided."

        elif action == "current_wallpaper":
            return get_current_wallpaper()

        elif action == "organize":
            return organize_desktop(params.get("mode", "by_type"))

        elif action == "clean":
            return clean_desktop()

        elif action == "list":
            return list_desktop()

        elif action == "stats":
            return get_desktop_stats()

        elif action == "task" or task:
            actual_task = task or params.get("description", "")
            if not actual_task:
                return "Please describe what you want to do on the desktop."

            if player:
                player.write_log("[Desktop] Generating action...")

            code = _ask_gemini_for_desktop_action(actual_task)
            return _execute_generated_code(code, player=player)

        else:
            if action:
                code = _ask_gemini_for_desktop_action(action)
                return _execute_generated_code(code, player=player)
            return "No action or task specified."

    except Exception as e:
        logger.error("Error: %s", e)
        return f"Desktop control error: {e}"