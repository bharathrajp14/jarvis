# mobile/mock_android.py — In-Memory Mock Android Device for Automated Verification
"""
Full mock Android Companion Device for testing mobile protocols, accessibility trees,
application flows (WhatsApp, YouTube, Instagram, Camera, Settings), and lock screen states.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from .protocol import AccessibilityNode, DeviceState

logger = logging.getLogger("JARVIS.MockAndroid")


class MockAndroidDevice:
    """Simulates an Android Companion device connected over WebSocket."""

    def __init__(self, device_id: str = "mock_android_pixel8", model: str = "Google Pixel 8 Pro"):
        self.device_id = device_id
        self.model = model
        self.battery_level = 88
        self.is_charging = False
        self.network_type = "WIFI"
        self.wifi_ssid = "JarvisSecureNet"
        self.foreground_app = "com.android.launcher"
        self.is_locked = False
        self.installed_apps = [
            "com.whatsapp",
            "com.google.android.youtube",
            "com.instagram.android",
            "com.google.android.apps.photos",
            "com.android.settings",
            "com.android.chrome",
        ]
        self.action_history: List[Dict[str, Any]] = []

    def set_lock_state(self, is_locked: bool) -> None:
        self.is_locked = is_locked
        if is_locked:
            self.foreground_app = "com.android.systemui.lockscreen"
        else:
            self.foreground_app = "com.android.launcher"

    def get_state(self) -> DeviceState:
        return DeviceState(
            device_id=self.device_id,
            model=self.model,
            battery_level=self.battery_level,
            is_charging=self.is_charging,
            network_type=self.network_type,
            wifi_ssid=self.wifi_ssid,
            foreground_app=self.foreground_app,
            is_screen_on=True,
            is_locked=self.is_locked,
            requires_biometric_or_pin=self.is_locked,
            installed_apps=self.installed_apps,
        )

    def get_accessibility_tree(self) -> AccessibilityNode:
        """Construct a realistic UI hierarchy based on foreground_app."""
        if self.is_locked:
            return AccessibilityNode(
                node_id=1,
                class_name="android.widget.FrameLayout",
                package_name="com.android.systemui",
                text="",
                view_id="lockscreen_root",
                children=[
                    AccessibilityNode(
                        node_id=2,
                        class_name="android.widget.TextView",
                        package_name="com.android.systemui",
                        text="Device Locked",
                        view_id="status_text",
                    ),
                    AccessibilityNode(
                        node_id=3,
                        class_name="android.widget.TextView",
                        package_name="com.android.systemui",
                        text="Enter PIN or Fingerprint",
                        view_id="pin_hint",
                    ),
                ],
            )

        if "whatsapp" in self.foreground_app.lower():
            return AccessibilityNode(
                node_id=10,
                class_name="android.widget.FrameLayout",
                package_name="com.whatsapp",
                text="",
                view_id="main_content",
                children=[
                    AccessibilityNode(
                        node_id=11,
                        class_name="android.widget.TextView",
                        package_name="com.whatsapp",
                        text="WhatsApp",
                        view_id="action_bar_title",
                    ),
                    AccessibilityNode(
                        node_id=12,
                        class_name="android.widget.EditText",
                        package_name="com.whatsapp",
                        text="",
                        view_id="search_src_text",
                        is_editable=True,
                        bounds=[50, 100, 1000, 200],
                    ),
                    AccessibilityNode(
                        node_id=13,
                        class_name="android.widget.TextView",
                        package_name="com.whatsapp",
                        text="Rahul",
                        view_id="contact_name",
                        is_clickable=True,
                        bounds=[50, 250, 1000, 350],
                    ),
                    AccessibilityNode(
                        node_id=14,
                        class_name="android.widget.TextView",
                        package_name="com.whatsapp",
                        text="Arun",
                        view_id="contact_name",
                        is_clickable=True,
                        bounds=[50, 370, 1000, 470],
                    ),
                    AccessibilityNode(
                        node_id=15,
                        class_name="android.widget.EditText",
                        package_name="com.whatsapp",
                        text="Type a message",
                        view_id="entry",
                        is_editable=True,
                        bounds=[50, 2000, 900, 2150],
                    ),
                    AccessibilityNode(
                        node_id=16,
                        class_name="android.widget.ImageButton",
                        package_name="com.whatsapp",
                        text="Send",
                        content_description="Send",
                        view_id="send",
                        is_clickable=True,
                        bounds=[920, 2000, 1050, 2150],
                    ),
                    AccessibilityNode(
                        node_id=17,
                        class_name="android.widget.ImageButton",
                        package_name="com.whatsapp",
                        text="Attach",
                        content_description="Attach document",
                        view_id="attach",
                        is_clickable=True,
                        bounds=[800, 2000, 900, 2150],
                    ),
                ],
            )

        if "youtube" in self.foreground_app.lower():
            return AccessibilityNode(
                node_id=20,
                class_name="android.widget.FrameLayout",
                package_name="com.google.android.youtube",
                text="",
                view_id="youtube_root",
                children=[
                    AccessibilityNode(
                        node_id=21,
                        class_name="android.widget.ImageView",
                        package_name="com.google.android.youtube",
                        text="Search",
                        content_description="Search YouTube",
                        view_id="menu_search",
                        is_clickable=True,
                        bounds=[850, 80, 950, 180],
                    ),
                    AccessibilityNode(
                        node_id=22,
                        class_name="android.widget.EditText",
                        package_name="com.google.android.youtube",
                        text="",
                        view_id="search_edit_text",
                        is_editable=True,
                        bounds=[100, 80, 800, 180],
                    ),
                    AccessibilityNode(
                        node_id=23,
                        class_name="android.widget.TextView",
                        package_name="com.google.android.youtube",
                        text="Python FastAPI Tutorial - Full Course",
                        view_id="video_title",
                        is_clickable=True,
                        bounds=[50, 300, 1000, 600],
                    ),
                ],
            )

        # Default Launcher Home Screen
        return AccessibilityNode(
            node_id=1,
            class_name="android.widget.FrameLayout",
            package_name="com.android.launcher",
            text="",
            view_id="launcher_workspace",
            children=[
                AccessibilityNode(
                    node_id=2,
                    class_name="android.widget.TextView",
                    package_name="com.android.launcher",
                    text="Google",
                    is_clickable=True,
                    bounds=[100, 200, 300, 350],
                ),
                AccessibilityNode(
                    node_id=3,
                    class_name="android.widget.TextView",
                    package_name="com.android.launcher",
                    text="WhatsApp",
                    is_clickable=True,
                    bounds=[350, 200, 550, 350],
                ),
                AccessibilityNode(
                    node_id=4,
                    class_name="android.widget.TextView",
                    package_name="com.android.launcher",
                    text="YouTube",
                    is_clickable=True,
                    bounds=[600, 200, 800, 350],
                ),
                AccessibilityNode(
                    node_id=5,
                    class_name="android.widget.TextView",
                    package_name="com.android.launcher",
                    text="Settings",
                    is_clickable=True,
                    bounds=[850, 200, 1050, 350],
                ),
            ],
        )

    def execute_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        act = action_data.get("action", "")
        self.action_history.append({"action": act, "data": action_data, "timestamp": time.time()})

        if act == "open_app":
            app = action_data.get("app_name", "").lower()
            if "whatsapp" in app:
                self.foreground_app = "com.whatsapp"
            elif "youtube" in app:
                self.foreground_app = "com.google.android.youtube"
            elif "settings" in app:
                self.foreground_app = "com.android.settings"
            else:
                self.foreground_app = f"com.example.{app}"
            return {"success": True, "action": "open_app", "foreground_app": self.foreground_app}

        if act == "press_home":
            self.foreground_app = "com.android.launcher"
            return {"success": True, "action": "press_home"}

        if act == "press_back":
            return {"success": True, "action": "press_back"}

        if act in ("click_coords", "click_node"):
            return {"success": True, "action": act, "details": action_data}

        if act == "type_text":
            return {"success": True, "action": "type_text", "text": action_data.get("text", "")}

        return {"success": True, "action": act}
