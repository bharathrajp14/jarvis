# tests/unit/test_terminal_viewport_scroll.py — Unit Tests for Virtual Viewport & Scrolling
from __future__ import annotations

from brjarvis.core.terminal.viewport import ScrollManager


class TestViewportScroll:
    """Test suite for ScrollManager, virtual viewport offset calculation, and auto-follow."""

    def test_initial_auto_follow_and_clamping(self):
        sm = ScrollManager(scroll_speed=3)
        # Total content 100 lines, viewport height 20 lines
        sm.update_dimensions(content_height=100, viewport_height=20)
        assert sm.auto_follow is True
        # Scrolled to bottom: 100 - 20 = 80
        assert sm.scroll_offset == 80

    def test_scroll_up_disables_auto_follow(self):
        sm = ScrollManager(scroll_speed=3)
        sm.update_dimensions(content_height=100, viewport_height=20)

        sm.scroll_up(lines=5)
        assert sm.auto_follow is False
        assert sm.scroll_offset == 75

        # Adding new content while scrolled up must not move scroll_offset
        sm.update_dimensions(content_height=110, viewport_height=20)
        assert sm.auto_follow is False
        assert sm.scroll_offset == 75

    def test_scroll_down_to_bottom_resumes_auto_follow(self):
        sm = ScrollManager(scroll_speed=3)
        sm.update_dimensions(content_height=100, viewport_height=20)
        sm.scroll_up(lines=10)
        assert sm.scroll_offset == 70
        assert sm.auto_follow is False

        # Scroll back down past maximum
        sm.scroll_down(lines=15)
        assert sm.scroll_offset == 80
        assert sm.auto_follow is True

    def test_visible_range_and_overscan(self):
        sm = ScrollManager(overscan=4)
        sm.update_dimensions(content_height=50, viewport_height=10)
        # Offset at bottom: 50 - 10 = 40
        v_range = sm.get_visible_range()
        assert v_range.is_at_bottom is True
        assert v_range.start_index == 40 - 4  # 36
        assert v_range.end_index == 50  # clamped to content_height

    def test_scrollbar_rendering(self):
        sm = ScrollManager()
        sm.update_dimensions(content_height=100, viewport_height=20)
        bar = sm.render_scrollbar(height=10)
        assert len(bar) == 10
        # Contains thumb character and track character
        assert "█" in bar
        assert "░" in bar
