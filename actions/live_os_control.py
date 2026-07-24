# actions/live_os_control.py — BR JARVIS MK37 Live Autonomous OS Controller
"""
Live Autonomous OS Visual Control Engine ("Antigravity Live Control").
Real-time screen perception, visual grounding, fast reaction loop, and continuous desktop automation.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import re
import sys
import time
from pathlib import Path

from actions.computer_control import (
    _screen_size,
    _take_screenshot_bytes,
    _click,
    _double_click,
    _right_click,
    _type_text,
    _smart_type,
    _hotkey,
    _press,
    _scroll,
    _drag,
    _move,
    _focus_window,
    _clear_field,
)

from core.native_bridge import fast_hash, grid_transform

_OS = platform.system()


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_api_key() -> str:
    for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(env, "").strip()
        if val:
            return val
    try:
        cfg_path = _base_dir() / "config" / "api_keys.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8")).get("gemini_api_key", "").strip()
    except Exception:
        pass
    return ""



try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pass


def _compress_screenshot(img_bytes: bytes) -> tuple[bytes, str]:
    """Compress screen frame to high-speed JPEG thumbnail (80x smaller payload, 5x faster inference)."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((1024, 768), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return img_bytes, "image/png"


def _call_vision_llm(img_bytes: bytes, system_instruction: str, api_key: str, model_name: str) -> str:
    """
    Ultra-Fast Resilient Vision LLM caller:
    1. Compresses image to high-speed JPEG (60KB).
    2. Calls local proxy gateway (http://localhost:8045/v1) with gemini-3.1-flash-image / gemini-3-flash.
    """
    import base64
    import urllib.request
    import json
    import time

    compressed_bytes, mime_type = _compress_screenshot(img_bytes)
    b64_img = base64.b64encode(compressed_bytes).decode("utf-8")

    # Models to try on local gateway in order of speed and stability
    gateway_models = ["gemini-3.1-flash-image", "gemini-3-flash", "gemini-3-flash-agent"]

    for gw_model in gateway_models:
        try:
            payload = {
                "model": gw_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": system_instruction},
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
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                content = body.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if content:
                    return content
        except Exception:
            continue

    # Fallback to Google GenAI Cloud API if gateway is offline
    try:
        from google import genai
        from google.genai import types as gtypes
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name if (model_name and "1.5" not in model_name) else "gemini-2.0-flash",
            contents=[
                gtypes.Part.from_bytes(data=compressed_bytes, mime_type=mime_type),
                system_instruction,
            ],
        )
        return (response.text or "").strip()
    except Exception as err:
        if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
            time.sleep(2.0)
            raise RuntimeError("Cloud quota exceeded (429). Cooldown active...") from err
        raise err


def _save_action_visualization(img_bytes: bytes, px_x: int, px_y: int, action: str, step: int) -> None:
    """Draw click target visualization (red crosshair) and action label for step trace."""
    try:
        from PIL import Image, ImageDraw
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)
        # Draw red circle around target
        r = 15
        draw.ellipse([px_x - r, px_y - r, px_x + r, px_y + r], outline="red", width=3)
        # Draw crosshair lines
        draw.line([px_x - 25, px_y, px_x + 25, px_y], fill="red", width=2)
        draw.line([px_x, px_y - 25, px_x, px_y + 25], fill="red", width=2)
        # Draw action text label
        draw.text((px_x + r + 5, px_y - 10), f"Step {step}: {action.upper()}", fill="red")
        
        debug_dir = Path("BR_WORKSPACE/Logs/live_os")
        debug_dir.mkdir(parents=True, exist_ok=True)
        img.save(debug_dir / f"step_{step}_action.png")
    except Exception:
        pass


class LiveOSController:
    """Autonomous Live OS Control Loop Engine."""

    def __init__(self, goal: str, max_steps: int = 50, step_delay: float = 0.5):
        self.goal = goal.strip()
        # 0 or <= 0 indicates Unlimited Mode
        if max_steps <= 0 or max_steps >= 99999:
            self.max_steps = 999999
        else:
            self.max_steps = max_steps
        self.step_delay = step_delay
        self.history: list[dict] = []
        self._last_img_hash: int | None = None

    def run(self, player=None, speak=None) -> str:
        """Execute the live visual control loop until goal is achieved or steps exhausted."""
        api_key = _get_api_key()
        if not api_key:
            return "Error: No API key available for Live OS Vision Controller."

        from config.models import get_model_for_task
        model_name = get_model_for_task("vision") or "gemini-3.1-flash-image"

        screen_w, screen_h = _screen_size()

        if player:
            player.write_log(f"[LiveOS] Starting task: '{self.goal}' on {screen_w}x{screen_h}")
        if speak:
            speak(f"Starting live OS control for: {self.goal}")

        limit_str = "Unlimited ♾️" if self.max_steps >= 999999 else f"{self.max_steps} steps"

        print(f"\n============================================================")
        print(f" 🤖 JARVIS LIVE OS CONTROL ENGINE (Antigravity Mode)")
        print(f" Goal: {self.goal}")
        print(f" Step Limit: {limit_str}")
        print(f" Screen Resolution: {screen_w}×{screen_h}")
        print(f" Vision Model: {model_name} (via Gateway / Fallback)")
        print(f"============================================================\n")

        # Antigravity Step 0 Shortcut Intent Check (0-Token Instant Action)
        try:
            from core.intent_engine import DeterministicIntentEngine
            from context.token_manager import TokenBudgetManager
            shortcut_res = DeterministicIntentEngine.parse_and_execute(self.goal)
            if shortcut_res and shortcut_res.get("executed"):
                TokenBudgetManager().record_usage(consumed=0, saved=2400, is_bypassed=True)
                msg = f"⚡ [Antigravity 0-Token Action]: {shortcut_res.get('result')}"
                print(f"➔ [Step 0/0] {msg}")
                return msg
        except Exception:
            pass

        for step in range(1, self.max_steps + 1):
            time.sleep(self.step_delay)

            # 1. Capture screen frame
            img_bytes = _take_screenshot_bytes()
            if not img_bytes:
                print(f"[LiveOS Step {step}] ⚠️ Failed to capture screenshot.")
                continue

            # Native C fast FNV-1a hash check for static screen detection
            img_hash = fast_hash(img_bytes)
            is_static = (img_hash == self._last_img_hash)
            self._last_img_hash = img_hash

            # Save step visualization for visual feedback & debugging
            try:
                debug_dir = Path("BR_WORKSPACE/Logs/live_os")
                debug_dir.mkdir(parents=True, exist_ok=True)
                step_path = debug_dir / f"step_{step}_capture.png"
                step_path.write_bytes(img_bytes)
            except Exception:
                pass

            # 2. Prepare visual prompt
            history_summary = ""
            if self.history:
                last_few = self.history[-4:]
                history_summary = "PAST ACTIONS TAKEN:\n" + "\n".join(
                    f" - Step {h['step']}: Action='{h['action']}', Target='{h.get('target','')}', Result='{h['result']}'"
                    for h in last_few
                )

            static_warning = ""
            if is_static and len(self.history) > 0:
                static_warning = (
                    "⚠️ WARNING: The screen state has NOT changed since your last action. "
                    "Your previous action may have missed the element or had no effect. Try double_click, "
                    "or verify target coordinates, or use a different approach.\n\n"
                )

            system_instruction = (
                f"You are JARVIS, an autonomous AI operating system controller. "
                f"Your goal is: '{self.goal}'.\n"
                f"Current screen resolution: {screen_w} width x {screen_h} height.\n"
                f"Coordinates scale: 0 to 1000 for x_norm and y_norm (where 0,0 is top-left, 1000,1000 is bottom-right).\n"
                f"{static_warning}"
                f"{history_summary}\n\n"
                f"Analyze the screenshot carefully. Identify open windows, input fields, buttons, icons, or text required to reach the goal.\n"
                f"Provide target element center point coordinates precisely.\n"
                f"Respond ONLY with a valid JSON object matching this schema:\n"
                f"{{\n"
                f'  "thought": "short explanation of visual analysis and next step",\n'
                f'  "action": "click" | "double_click" | "right_click" | "type" | "hotkey" | "press" | "drag" | "scroll" | "focus" | "wait" | "done" | "fail",\n'
                f'  "x_norm": 0..1000,\n'
                f'  "y_norm": 0..1000,\n'
                f'  "text": "text to type if action is type",\n'
                f'  "keys": "hotkey combo like ctrl+t or enter if action is hotkey/press",\n'
                f'  "reason": "why this action is taken",\n'
                f'  "done": true/false\n'
                f"}}\n"
            )

            try:
                raw_text = _call_vision_llm(img_bytes, system_instruction, api_key, model_name)
                # Clean JSON fences if present
                clean_json = re.sub(r"```(?:json)?", "", raw_text).strip().rstrip("`").strip()
                data = json.loads(clean_json)
            except Exception as e:
                print(f"[LiveOS Step {step}] ⚠️ Vision inference parsing failed: {e}")
                continue

            thought = data.get("thought", "")
            action = data.get("action", "wait").lower().strip()
            x_norm = data.get("x_norm")
            y_norm = data.get("y_norm")
            text_val = data.get("text", "")
            keys_val = data.get("keys", "")
            is_done = data.get("done", False)

            # Native hardware grid transform: (0..1000) -> actual pixels
            px_x, px_y = None, None
            if x_norm is not None and y_norm is not None:
                try:
                    px_x, px_y = grid_transform(int(x_norm), int(y_norm), screen_w, screen_h)
                except Exception:
                    px_x, px_y = None, None

            # Visual trace of click target coordinates
            if px_x is not None and px_y is not None:
                _save_action_visualization(img_bytes, px_x, px_y, action, step)

            print(f"➔ [Step {step}/{self.max_steps}] Thought: {thought}")
            print(f"   Action: '{action}' | Target Coords: ({px_x}, {px_y}) | Input: '{text_val or keys_val}'")

            if player:
                player.write_log(f"[LiveOS #{step}] {action} -> ({px_x},{px_y})")

            # 3. Execute OS action
            result_str = ""
            try:
                if action == "done" or is_done:
                    summary = f"Goal achieved in {step} steps: {thought}"
                    print(f"\n✅ {summary}\n")
                    if speak:
                        speak("Task completed successfully, sir.")
                    return summary

                if action == "fail":
                    summary = f"Task marked unachievable at step {step}: {thought}"
                    print(f"\n❌ {summary}\n")
                    return summary

                if action == "click" and px_x is not None and px_y is not None:
                    result_str = _click(px_x, px_y, "left")

                elif action == "double_click" and px_x is not None and px_y is not None:
                    result_str = _double_click(px_x, px_y)

                elif action == "right_click" and px_x is not None and px_y is not None:
                    result_str = _right_click(px_x, px_y)

                elif action == "type":
                    if px_x is not None and px_y is not None:
                        _click(px_x, px_y, "left")
                        time.sleep(0.1)
                    result_str = _smart_type(text_val, clear_first=False)

                elif action == "hotkey":
                    result_str = _hotkey(*[k.strip() for k in keys_val.split("+")])

                elif action == "press":
                    result_str = _press(keys_val or "enter")

                elif action == "scroll":
                    result_str = _scroll("down" if (y_norm or 500) > 500 else "up", 4)

                elif action == "focus":
                    result_str = _focus_window(text_val)

                elif action == "wait":
                    time.sleep(1.0)
                    result_str = "Waited 1s"
                else:
                    result_str = f"Executed generic action: {action}"

            except Exception as ex:
                result_str = f"Action execution error: {ex}"
                print(f"   ⚠️ Action error: {ex}")

            self.history.append({
                "step": step,
                "action": action,
                "target": f"({px_x},{px_y})" if px_x is not None else "",
                "result": result_str
            })

        summary = f"Live OS Control reached maximum step limit ({self.max_steps}). Goal: {self.goal}"
        print(f"\n⚠️ {summary}\n")
        return summary


def live_os_control_action(parameters: dict, player=None, speak=None) -> str:
    goal = parameters.get("goal", "").strip()
    if not goal:
        return "Please provide a goal for Live OS Control, sir."

    raw_steps = parameters.get("max_steps", 50)
    try:
        max_steps = int(raw_steps)
    except Exception:
        max_steps = 0 if "unlim" in str(raw_steps).lower() else 50

    controller = LiveOSController(goal=goal, max_steps=max_steps)
    return controller.run(player=player, speak=speak)
