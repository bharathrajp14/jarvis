# tests/test_vision_engine.py — Unit Tests for Priority 9 Vision Engine
from __future__ import annotations

import pytest
from vision.engine import VisionEngine, get_vision_engine
from vision.ocr_engine import OCREngine
from vision.screen_analyst import ScreenAnalyst
from vision.types import ScreenAnalysisReport, ScreenBoundingBox


def test_screen_analyst_capture():
    analyst = ScreenAnalyst()
    raw_bytes, w, h, frame_hash = analyst.capture_frame()
    if len(raw_bytes) == 0 or frame_hash == 0:
        pytest.skip("Headless test environment: display capture or mss is unavailable")
        
    assert w > 0 and h > 0
    assert isinstance(frame_hash, int)

    # First call registers hash
    is_first = analyst.is_frame_unchanged(frame_hash)
    assert is_first is False

    # Second call with same hash returns True
    is_second = analyst.is_frame_unchanged(frame_hash)
    assert is_second is True


def test_ocr_engine():
    ocr = OCREngine()
    text, elements = ocr.extract_text_and_elements(b"frame_bytes", 1920, 1080)
    assert "Admin" in text
    assert len(elements) > 0

    elem = ocr.find_element_by_label("Settlements", elements)
    assert elem is not None
    assert elem.label == "Settlements Tab"


def test_vision_engine_analysis():
    vision = get_vision_engine()
    report = vision.analyze_screen(force_refresh=True)

    assert isinstance(report, ScreenAnalysisReport)
    assert report.screen_width > 0
    assert report.screen_height > 0
