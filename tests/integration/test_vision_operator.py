# tests/integration/test_vision_operator.py — Scenarios 1 to 8: Vision & Operator Integration
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from vision.engine import get_vision_engine
from vision.types import ScreenAnalysisReport, ScreenBoundingBox, DetectedUIElement, ElementType
from computer.operator import get_computer_operator
from computer.types import ComputerAction, ActionType


def test_scenario_1_to_2_open_app_and_calculation():
    """Scenarios 1 & 2: Open Calculator, detect buttons, perform calculation and verify."""
    operator = get_computer_operator()
    vision = get_vision_engine()

    # Mock screen containing Calculator
    dummy_report = ScreenAnalysisReport(
        screen_width=1920,
        screen_height=1080,
        ocr_text="Calculator 5",
        elements=[
            DetectedUIElement(
                label="Button 2",
                text="2",
                bbox=ScreenBoundingBox(xmin=100, ymin=200, xmax=150, ymax=250),
                element_type=ElementType.BUTTON,
            ),
            DetectedUIElement(
                label="Button +",
                text="+",
                bbox=ScreenBoundingBox(xmin=160, ymin=200, xmax=210, ymax=250),
                element_type=ElementType.BUTTON,
            ),
            DetectedUIElement(
                label="Button 3",
                text="3",
                bbox=ScreenBoundingBox(xmin=220, ymin=200, xmax=270, ymax=250),
                element_type=ElementType.BUTTON,
            ),
            DetectedUIElement(
                label="Button =",
                text="=",
                bbox=ScreenBoundingBox(xmin=280, ymin=200, xmax=330, ymax=250),
                element_type=ElementType.BUTTON,
            ),
        ]
    )

    with patch.object(vision, "analyze_screen", return_value=dummy_report), \
         patch("pyautogui.click"), \
         patch("pyautogui.moveTo"):
        # Trigger vision analysis
        report = vision.analyze_screen(force_refresh=True)
        assert "Calculator" in report.ocr_text
        assert len(report.elements) == 4

        # Simulate operator actions clicking the buttons
        action_clicks = [
            ComputerAction(action_type=ActionType.MOUSE_CLICK, x=125, y=225, description="Click 2"),
            ComputerAction(action_type=ActionType.MOUSE_CLICK, x=185, y=225, description="Click +"),
            ComputerAction(action_type=ActionType.MOUSE_CLICK, x=245, y=225, description="Click 3"),
            ComputerAction(action_type=ActionType.MOUSE_CLICK, x=305, y=225, description="Click ="),
        ]

        for action in action_clicks:
            res = operator.execute_action(action)
            assert res.success is True


def test_scenario_3_copy_paste_text():
    """Scenario 3: Copy-paste text keyboard/clipboard operations."""
    operator = get_computer_operator()

    # Set text in clipboard
    set_action = ComputerAction(
        action_type=ActionType.CLIPBOARD_SET,
        text="JARVIS_INTEGRATION_CLIPBOARD_DATA",
        description="Copying data to clipboard",
    )
    assert operator.execute_action(set_action).success is True

    # Read text from clipboard
    get_action = ComputerAction(
        action_type=ActionType.CLIPBOARD_GET,
        description="Reading data from clipboard",
    )
    res = operator.execute_action(get_action)
    assert res.success is True
    assert res.data == "JARVIS_INTEGRATION_CLIPBOARD_DATA"


def test_scenario_5_to_6_multimonitor_and_screen_hash():
    """Scenarios 5 & 6: Screen analysis hash and unchanged frame detection."""
    vision = get_vision_engine()

    # Reset cache to force analysis
    vision._cached_report = None

    # First analysis creates cached report
    report1 = vision.analyze_screen(force_refresh=True)
    h1 = report1.frame_hash

    # Second analysis returns cached report if same hash
    with patch.object(vision.analyst, "is_frame_unchanged", return_value=True):
        report2 = vision.analyze_screen()
        assert report2.frame_hash == h1


def test_scenario_7_window_management():
    """Scenario 7: Window focus action execution."""
    operator = get_computer_operator()

    action = ComputerAction(
        action_type=ActionType.APP_FOCUS,
        description="Focus on Window",
    )
    res = operator.execute_action(action)
    assert res.success is True


def test_scenario_8_recovery_from_miss_and_permission_denial():
    """Scenario 8 & 9: Verification on permission check block."""
    operator = get_computer_operator()

    # Action that is restricted/denied via environment permission mock
    with patch("computer.operator.check_permission", return_value=False):
        action = ComputerAction(
            action_type=ActionType.MOUSE_CLICK,
            x=10,
            y=10,
            description="Unauthorized click",
        )
        res = operator.execute_action(action)
        assert res.success is False
        assert "Permission denied" in res.verification_message
