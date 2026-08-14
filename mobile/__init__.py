# mobile/__init__.py — Mobile Master Control Subsystem
"""
BR JARVIS MK37 Mobile Master Control Subsystem.
Provides Android device gateway, secure WebSocket pairing, accessibility protocols,
multimodal screen understanding, and cross-device task coordination.
"""
from mobile.protocol import MobileMessage, MobileMessageType, AccessibilityNode, DeviceState
from mobile.gateway import get_device_gateway, DeviceGateway, PairedDevice
from mobile.device_controller import AndroidDeviceController
from mobile.mock_android import MockAndroidDevice

__all__ = [
    "MobileMessage",
    "MobileMessageType",
    "AccessibilityNode",
    "DeviceState",
    "get_device_gateway",
    "DeviceGateway",
    "PairedDevice",
    "AndroidDeviceController",
    "MockAndroidDevice",
]
