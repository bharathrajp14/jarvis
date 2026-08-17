# tests/unit/test_terminal_selection_clipboard.py — Unit Tests for Selection and Clipboard
from __future__ import annotations

import pytest
from unittest.mock import patch
from brjarvis.core.terminal.selection import (
    ClipboardProvider,
    SelectionManager,
    SelectionMode,
    SelectionRange,
)


class TestSelectionAndClipboard:
    """Test suite for text selection, word boundaries, and clipboard handling."""

    def test_selection_range_normalization(self):
        # Forward drag
        sr_fwd = SelectionRange(start_row=1, start_col=5, end_row=3, end_col=10, mode=SelectionMode.CHAR)
        assert sr_fwd.normalized() == ((1, 5), (3, 10))

        # Backward drag
        sr_bwd = SelectionRange(start_row=3, start_col=10, end_row=1, end_col=5, mode=SelectionMode.CHAR)
        assert sr_bwd.normalized() == ((1, 5), (3, 10))

    def test_word_selection_path_detection(self):
        sm = SelectionManager()
        line = "Check file at src/brjarvis/core/runtime.py:120 for details."
        # Click on 'runtime' (index ~30)
        start, end = sm.select_word_at(line, row=0, col=30)
        extracted = line[start:end]
        assert "src/brjarvis/core/runtime.py:120" == extracted

    def test_multiline_text_extraction(self):
        sm = SelectionManager()
        lines = [
            "Line 0: start of log",
            "Line 1: important event occurred",
            "Line 2: end of log",
        ]
        # Select from 'start' in line 0 (col 8) to 'event' in line 1 (col 23)
        sm.start_selection(row=0, col=8, mode=SelectionMode.CHAR)
        sm.update_selection(row=1, col=23)

        text = sm.extract_selected_text(lines)
        assert text == "start of log\nLine 1: important event"

    def test_clipboard_fallback_safety(self):
        # ClipboardProvider should never raise exceptions
        with patch.object(ClipboardProvider, "_copy_osc52", return_value=True):
            res = ClipboardProvider.copy("Test Clipboard")
            assert res is True
