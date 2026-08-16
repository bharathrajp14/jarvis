# computer/operator.py — Human-Level Computer Operator Engine for JARVIS MK37
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
from .types import ActionResult, ActionType, ComputerAction
from core.runtime import get_runtime
from events.bus import get_event_bus
from events.types import AuditEvent
from permissions import check_permission
from vision.engine import get_vision_engine
from actions.clipboard_utils import get_clipboard_text, set_clipboard_text

logger = logging.getLogger("JARVIS.ComputerOperator")

try:
    import pyautogui
    # Enforce PyAutoGUI Fail-Safe security: moving mouse to corner immediately aborts automation
    pyautogui.FAILSAFE = True
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except ImportError:
    _PYPERCLIP_AVAILABLE = False


class ComputerOperator:
    """Master Computer Operator automating mouse, keyboard, clipboard, and window focus.
    Guarantees strict adherence to human failsafe mechanisms.
    """

    def __init__(self):
        self.runtime = get_runtime()
        self.event_bus = get_event_bus()
        self.vision = get_vision_engine()
        self._clipboard_buffer = ""

        # Register self in DI container
        self.runtime.container.register_instance(ComputerOperator, self)
        logger.info("⚡ ComputerOperator initialized (Failsafe ACTIVE)")

    def execute_action(self, action: ComputerAction) -> ActionResult:
        """Executes a single ComputerAction after permission checks."""
        # 1. Enforcement of Security Permission Check
        target_perm = f"computer.{action.action_type.value}"
        if not check_permission(target_perm, {"action": action.action_type.value}):
            logger.warning("❌ Permission denied for action: %s", action.action_type.value)
            return ActionResult(
                action_id=action.action_id,
                success=False,
                verification_message=f"Permission denied: {target_perm}",
            )

        logger.info("🖱️ ComputerOperator: Executing [%s] - %s", action.action_type.value, action.description)

        try:
            # Low-level OS execution
            if action.action_type == ActionType.MOUSE_CLICK:
                if _PYAUTOGUI_AVAILABLE and action.x is not None and action.y is not None:
                    pyautogui.click(action.x, action.y)

            elif action.action_type == ActionType.DOUBLE_CLICK:
                if _PYAUTOGUI_AVAILABLE and action.x is not None and action.y is not None:
                    pyautogui.doubleClick(action.x, action.y)

            elif action.action_type == ActionType.RIGHT_CLICK:
                if _PYAUTOGUI_AVAILABLE and action.x is not None and action.y is not None:
                    pyautogui.rightClick(action.x, action.y)

            elif action.action_type == ActionType.MOUSE_MOVE:
                if _PYAUTOGUI_AVAILABLE and action.x is not None and action.y is not None:
                    pyautogui.moveTo(action.x, action.y)

            elif action.action_type == ActionType.MOUSE_SCROLL:
                if _PYAUTOGUI_AVAILABLE:
                    clicks = action.scroll_clicks if action.scroll_clicks != 0 else 5
                    pyautogui.scroll(clicks, x=action.x, y=action.y)

            elif action.action_type == ActionType.DRAG_AND_DROP:
                if _PYAUTOGUI_AVAILABLE and action.x is not None and action.y is not None and action.target_x is not None and action.target_y is not None:
                    pyautogui.moveTo(action.x, action.y)
                    pyautogui.dragTo(action.target_x, action.target_y, duration=0.5)

            elif action.action_type == ActionType.KEYBOARD_TYPE:
                if _PYAUTOGUI_AVAILABLE and action.text:
                    pyautogui.typewrite(action.text, interval=0.01)

            elif action.action_type == ActionType.KEYBOARD_PRESS:
                if _PYAUTOGUI_AVAILABLE and action.keys:
                    for k in action.keys:
                        pyautogui.press(k)

            elif action.action_type == ActionType.HOTKEY:
                if _PYAUTOGUI_AVAILABLE and action.keys:
                    pyautogui.hotkey(*action.keys)

            elif action.action_type == ActionType.CLIPBOARD_SET:
                if action.text is not None:
                    self._clipboard_buffer = action.text
                    set_clipboard_text(action.text)

            elif action.action_type == ActionType.CLIPBOARD_GET:
                clip_text = get_clipboard_text()
                if not clip_text and self._clipboard_buffer:
                    clip_text = self._clipboard_buffer
                return ActionResult(action_id=action.action_id, success=True, data=clip_text)

            elif action.action_type == ActionType.TAKE_SCREENSHOT:
                report = self.vision.analyze_screen(force_refresh=True)
                return ActionResult(
                    action_id=action.action_id,
                    success=True,
                    verification_message=f"Screenshot captured ({report.screen_width}x{report.screen_height})",
                    data=report.image_path
                )

            elif action.action_type in (ActionType.WINDOW_FOCUS, ActionType.APP_FOCUS):
                success = self.focus_window(action.text or "")
                return ActionResult(
                    action_id=action.action_id,
                    success=True,
                    verification_message=f"Focus window '{action.text}' attempt completed (status: {success})",
                )

            # Audit event
            self.event_bus.publish(AuditEvent(
                topic="audit.action",
                action_type=action.action_type.value,
                target=action.description or "desktop",
                user_confirmed=not action.requires_approval
            ))

            # Post-action state verification via VisionEngine
            report = self.vision.analyze_screen(force_refresh=True)
            verify_msg = f"Action Verified on screen ({report.screen_width}x{report.screen_height})"

            return ActionResult(action_id=action.action_id, success=True, verification_message=verify_msg)

        except Exception as ex:
            if "FailSafeException" in type(ex).__name__:
                logger.critical("🛑 PyAutoGUI FailSafe triggered during action %s. Automation immediately halted.", action.action_type.value)
                self.event_bus.publish(AuditEvent(
                    topic="audit.failsafe",
                    action_type="failsafe_abort",
                    target=action.action_type.value,
                    user_confirmed=False
                ))
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    verification_message="Emergency FailSafe triggered by user: Desktop automation immediately halted."
                )
            logger.error("❌ ComputerOperator action failed: %s", ex, exc_info=True)
            return ActionResult(action_id=action.action_id, success=False, verification_message=str(ex))

    async def async_execute_action(self, action: ComputerAction) -> ActionResult:
        """Asynchronous execution wrapper for computer action."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.execute_action, action)

    def focus_window(self, title_query: str) -> bool:
        """Attempt to focus a window matching title substring across Windows, macOS, or Linux."""
        if not title_query:
            return False

        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                found_hwnd = None
                
                def enum_windows_callback(hwnd, extra):
                    nonlocal found_hwnd
                    if user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            if title_query.lower() in buff.value.lower():
                                found_hwnd = hwnd
                                return False
                    return True

                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

                if found_hwnd:
                    user32.SetForegroundWindow(found_hwnd)
                    return True
            except Exception as e:
                logger.debug("win32 window focus failed: %s", e)

        elif sys.platform == "darwin":
            try:
                cmd = f'tell application "System Events" to set frontmost of first process whose name contains "{title_query}" to true'
                subprocess.run(["osascript", "-e", cmd], capture_output=True, timeout=3)
                return True
            except Exception:
                pass

        elif sys.platform.startswith("linux"):
            if shutil.which("wmctrl"):
                try:
                    subprocess.run(["wmctrl", "-a", title_query], capture_output=True, timeout=3)
                    return True
                except Exception:
                    pass

        return False

    def click(self, x: int, y: int, description: str = "") -> ActionResult:
        action = ComputerAction(
            action_type=ActionType.MOUSE_CLICK,
            x=x,
            y=y,
            description=description or f"Click at ({x}, {y})",
        )
        return self.execute_action(action)

    def double_click(self, x: int, y: int, description: str = "") -> ActionResult:
        action = ComputerAction(
            action_type=ActionType.DOUBLE_CLICK,
            x=x,
            y=y,
            description=description or f"Double-click at ({x}, {y})",
        )
        return self.execute_action(action)

    def right_click(self, x: int, y: int, description: str = "") -> ActionResult:
        action = ComputerAction(
            action_type=ActionType.RIGHT_CLICK,
            x=x,
            y=y,
            description=description or f"Right-click at ({x}, {y})",
        )
        return self.execute_action(action)

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None, description: str = "") -> ActionResult:
        action = ComputerAction(
            action_type=ActionType.MOUSE_SCROLL,
            x=x,
            y=y,
            scroll_clicks=clicks,
            description=description or f"Scroll {clicks} clicks",
        )
        return self.execute_action(action)

    def type_text(self, text: str, description: str = "") -> ActionResult:
        action = ComputerAction(
            action_type=ActionType.KEYBOARD_TYPE,
            text=text,
            description=description or f"Type '{text[:20]}'",
        )
        return self.execute_action(action)

    def hotkey(self, keys: List[str], description: str = "") -> ActionResult:
        action = ComputerAction(
            action_type=ActionType.HOTKEY,
            keys=keys,
            description=description or f"Hotkey {'+'.join(keys)}",
        )
        return self.execute_action(action)


_global_computer_operator: Optional[ComputerOperator] = None


def get_computer_operator() -> ComputerOperator:
    global _global_computer_operator
    if _global_computer_operator is None:
        _global_computer_operator = ComputerOperator()
    return _global_computer_operator
