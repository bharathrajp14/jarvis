# tests/unit/test_ui_comprehensive_flaws.py — Unit tests validating UI flaw fixes
import pytest
from unittest.mock import MagicMock
from ui.app import HeadlessJarvisUI
from ui.widgets import LogWidget, SubAgentTaskWidget, FileDropZone
from ui.overlays import HueWheel
from ui_mark import _generate_remote_credentials
import ui._qt as _qt


def test_headless_ui_agent_task_signature():
    """Verify HeadlessJarvisUI accepts the standard (task_id, name, status, progress, result) signature."""
    ui = HeadlessJarvisUI()
    ui.update_agent_task("task-123", "Data Ingestion", "running", 0.45, "Fetching records")
    assert "task-123" in ui._agent_tasks
    assert ui._agent_tasks["task-123"]["name"] == "Data Ingestion"
    assert ui._agent_tasks["task-123"]["progress"] == 0.45
    assert ui._agent_tasks["task-123"]["result"] == "Fetching records"

    ui.remove_agent_task("task-123")
    assert "task-123" not in ui._agent_tasks


def test_log_widget_tag_matching():
    """Ensure routine words containing 'err' (e.g. transferring, interrupted) are not tagged as 'err'."""
    if not _qt._HAS_QT:
        pytest.skip("Qt not available in environment")

    app = _qt.QApplication.instance() or _qt.QApplication([])
    widget = LogWidget()
    
    # Test ordinary words containing substring 'err'
    widget._queue.append("SYS: Transferring files to remote...")
    widget._next()
    assert widget._tag == "sys", f"Expected 'sys', got '{widget._tag}'"

    widget._queue.append("SYS: Operation interrupted by user")
    widget._next()
    assert widget._tag == "sys", f"Expected 'sys', got '{widget._tag}'"

    # Test genuine errors
    widget._queue.append("ERR: Network timeout")
    widget._next()
    assert widget._tag == "err", f"Expected 'err', got '{widget._tag}'"

    widget._queue.append("Error: Failed to connect to server")
    widget._next()
    assert widget._tag == "err", f"Expected 'err', got '{widget._tag}'"


def test_hue_wheel_angle_math():
    """Verify HueWheel clockwise coordinate math correctly maps cardinal points."""
    if not _qt._HAS_QT:
        pytest.skip("Qt not available in environment")

    app = _qt.QApplication.instance() or _qt.QApplication([])
    wheel = HueWheel("#00f2fe")
    
    # Center is at (74, 74) for a 148x148 widget
    c = _qt.QPointF(74, 74)
    
    # Point at 3 o'clock (+X, dy=0) -> Hue ~ 0.0
    h_3 = wheel._hue_from_pos(_qt.QPointF(124, 74))
    assert abs(h_3 - 0.0) < 0.02 or abs(h_3 - 1.0) < 0.02

    # Point at 6 o'clock (dx=0, +Y) -> Hue ~ 0.25
    h_6 = wheel._hue_from_pos(_qt.QPointF(74, 124))
    assert abs(h_6 - 0.25) < 0.02

    # Point at 9 o'clock (-X, dy=0) -> Hue ~ 0.50
    h_9 = wheel._hue_from_pos(_qt.QPointF(24, 74))
    assert abs(h_9 - 0.50) < 0.02

    # Point at 12 o'clock (dx=0, -Y) -> Hue ~ 0.75
    h_12 = wheel._hue_from_pos(_qt.QPointF(74, 24))
    assert abs(h_12 - 0.75) < 0.02


def test_file_drop_zone_clear_signal():
    """Verify clear_file on FileDropZone emits empty string signal."""
    if not _qt._HAS_QT:
        pytest.skip("Qt not available in environment")

    app = _qt.QApplication.instance() or _qt.QApplication([])
    zone = FileDropZone()
    emitted = []
    zone.file_selected.connect(lambda path: emitted.append(path))

    zone._set_file("sample.txt")
    assert emitted[-1] == "sample.txt"
    assert zone.current_file() == "sample.txt"

    zone.clear_file()
    assert emitted[-1] == ""
    assert zone.current_file() is None


def test_subagent_task_widget_dynamic_result():
    """Verify SubAgentTaskWidget dynamically creates/updates result label."""
    if not _qt._HAS_QT:
        pytest.skip("Qt not available in environment")

    app = _qt.QApplication.instance() or _qt.QApplication([])
    widget = SubAgentTaskWidget("task-1", "Search Task", "running", 0.1, "")
    assert widget.result_label.isHidden()

    widget.update_task("Search Task", "completed", 1.0, "Found 12 sources")
    assert widget.result_label.text() == "Found 12 sources"
    assert not widget.result_label.isHidden()


def test_generate_remote_credentials():
    """Verify _generate_remote_credentials returns valid 4-tuple with URL, token, and QR payload."""
    creds = _generate_remote_credentials()
    assert creds is not None
    base_url, key, auto_url, manual_url = creds
    assert base_url.startswith("http://")
    assert len(key) >= 4
    assert f"token={key}" in auto_url
    assert manual_url == base_url
