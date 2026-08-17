# actions/automation_engine.py — Universal Automation & Workflow Engine for BR-Jarvis
"""
Universal Automation Engine for BR-Jarvis.
Enables application lifecycle control, mouse/keyboard macro automation,
system command execution, and multi-step JSON workflow scripting.
"""
from __future__ import annotations

import os
import sys
import time
import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.AutomationEngine")


class UniversalAutomationEngine:
    """
    General-purpose OS, application, and workflow automation engine.
    """

    def __init__(self):
        pass

    def launch_app(self, app_name: str, url: str = "") -> str:
        """Launch an application or web URL."""
        from brjarvis.actions.open_app import open_app
        return open_app(parameters={"app_name": app_name, "url": url})

    def close_app(self, identifier: str) -> str:
        """Terminate or close an application by name or PID."""
        from brjarvis.tools.process_tools import kill_process
        return kill_process({"identifier": identifier})

    def focus_app(self, title: str) -> str:
        """Focus/bring application window to front by title."""
        from brjarvis.tools.window_manager import window_manager_action
        return window_manager_action({"action": "focus", "title": title})

    def execute_shell(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a shell or PowerShell command safely and return output.
        """
        if not command:
            return {"success": False, "output": "No command provided", "returncode": -1}

        if sys.platform == "win32":
            cmd = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ]
        else:
            cmd = ["/bin/bash", "-lc", command] if os.path.exists("/bin/bash") else ["/bin/sh", "-lc", command]

        try:
            res = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()
            output = stdout if stdout else stderr
            return {
                "success": res.returncode == 0,
                "output": output or "Command completed with no output.",
                "returncode": res.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": f"Command timed out after {timeout} seconds.", "returncode": -1}
        except Exception as e:
            return {"success": False, "output": f"Shell execution error: {e}", "returncode": -1}

    def execute_ui_macro(self, action: str, **kwargs) -> str:
        """
        Execute mouse/keyboard UI automation macro step.
        """
        from brjarvis.actions.computer_control import computer_control

        act_map = {
            "click": "click",
            "double_click": "double_click",
            "move": "move",
            "type": "smart_type",
            "type_text": "smart_type",
            "hotkey": "hotkey",
            "press": "press"
        }
        target_action = act_map.get(action.lower(), action)
        params = {"action": target_action}
        params.update(kwargs)
        return computer_control(parameters=params)

    def run_workflow_script(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run a sequential multi-step workflow automation script.
        """
        results = []
        overall_success = True

        for idx, step in enumerate(steps, 1):
            act = step.get("action", "").lower()
            step_desc = f"Step {idx} ({act})"
            logger.info(f"⚡ Automation Workflow: Executing {step_desc}")

            try:
                if act in ("launch", "launch_app", "open_app"):
                    res_str = self.launch_app(step.get("app_name", ""), url=step.get("url", ""))
                    results.append({step_desc: res_str})

                elif act in ("close", "close_app", "kill"):
                    res_str = self.close_app(step.get("identifier", step.get("app_name", "")))
                    results.append({step_desc: res_str})

                elif act in ("focus", "focus_app"):
                    res_str = self.focus_app(step.get("title", ""))
                    results.append({step_desc: res_str})

                elif act in ("sleep", "wait"):
                    sec = float(step.get("seconds", step.get("delay", 1.0)))
                    time.sleep(sec)
                    results.append({step_desc: f"Slept for {sec} seconds."})

                elif act in ("shell", "exec", "command"):
                    shell_res = self.execute_shell(step.get("command", ""), timeout=step.get("timeout", 30))
                    results.append({step_desc: shell_res["output"]})
                    if not shell_res["success"]:
                        overall_success = False

                elif act in ("type", "type_text", "write"):
                    ui_res = self.execute_ui_macro("type_text", text=step.get("text", ""))
                    results.append({step_desc: ui_res})

                elif act in ("hotkey", "press_key"):
                    keys = step.get("keys", step.get("key", ""))
                    ui_res = self.execute_ui_macro("hotkey", keys=keys)
                    results.append({step_desc: ui_res})

                elif act in ("click", "double_click", "move"):
                    ui_res = self.execute_ui_macro(
                        act,
                        x=step.get("x"),
                        y=step.get("y"),
                        button=step.get("button", "left")
                    )
                    results.append({step_desc: ui_res})

                elif act in ("whatsapp", "send_whatsapp"):
                    from brjarvis.actions.whatsapp_automation import get_whatsapp_automation
                    wa = get_whatsapp_automation()
                    wa_res = wa.send_message(step.get("recipient", ""), step.get("message", step.get("text", "")))
                    results.append({step_desc: wa_res})

                elif act in ("calendar", "create_calendar_event", "calendar_event"):
                    from brjarvis.actions.calendar_engine import get_calendar_engine
                    cal = get_calendar_engine()
                    cal_res = cal.create_event(
                        title=step.get("title", ""),
                        start_time_str=step.get("start_time", step.get("time", "")),
                        description=step.get("description", ""),
                        location=step.get("location", ""),
                        attendees=step.get("attendees"),
                        notify_whatsapp=step.get("notify_whatsapp", False)
                    )
                    results.append({step_desc: str(cal_res)})

                elif act in ("email", "send_email"):
                    from brjarvis.actions.smart_email_sender import get_smart_email_sender
                    sender = get_smart_email_sender()
                    email_res = sender.send_email(
                        recipient=step.get("recipient", step.get("to", "")),
                        subject=step.get("subject", ""),
                        body=step.get("body", step.get("text", "")),
                        attachment_paths=step.get("attachment_paths", step.get("attachments"))
                    )
                    results.append({step_desc: email_res})

                else:
                    results.append({step_desc: f"Unknown automation action '{act}'"})
                    overall_success = False

            except Exception as e:
                err_msg = f"Error in {step_desc}: {e}"
                logger.error(err_msg)
                results.append({step_desc: err_msg})
                overall_success = False

        return {
            "success": overall_success,
            "step_count": len(steps),
            "results": results
        }


# Global singleton instance
_automation_engine = UniversalAutomationEngine()


def get_automation_engine() -> UniversalAutomationEngine:
    return _automation_engine
