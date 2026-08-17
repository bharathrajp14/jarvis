# tests/unit/test_terminal_hit_test.py — Unit Tests for Spatial Hit-Testing
from __future__ import annotations

import pytest
from brjarvis.core.terminal.hit_test import (
    HitTestManager,
    InteractiveRegion,
    RegionType,
)


class TestHitTestManager:
    """Test suite for spatial hit-testing and interactive regions."""

    def test_region_containment(self):
        reg = InteractiveRegion(
            id="test_btn",
            region_type=RegionType.BUTTON,
            x=10,
            y=5,
            width=20,
            height=2,
        )
        assert reg.contains(10, 5) is True
        assert reg.contains(29, 6) is True
        assert reg.contains(9, 5) is False
        assert reg.contains(30, 5) is False
        assert reg.contains(15, 7) is False

    def test_hit_test_resolution_and_priority(self):
        mgr = HitTestManager()
        # Lower priority background region
        mgr.register(
            region_id="bg",
            region_type=RegionType.STATUS_ITEM,
            x=0,
            y=0,
            width=50,
            height=10,
            priority=1,
        )
        # Higher priority button on top
        mgr.register(
            region_id="btn_ok",
            region_type=RegionType.BUTTON,
            x=10,
            y=5,
            width=10,
            height=1,
            priority=20,
            action="dialog:accept",
        )

        # Hit outside button but inside bg
        hit_bg = mgr.hit_test(5, 5)
        assert hit_bg is not None
        assert hit_bg.id == "bg"

        # Hit on button -> returns higher priority button
        hit_btn = mgr.hit_test(12, 5)
        assert hit_btn is not None
        assert hit_btn.id == "btn_ok"
        assert hit_btn.action_name == "dialog:accept"

    def test_hover_updates(self):
        mgr = HitTestManager()
        mgr.register("link_1", RegionType.LINK, x=5, y=2, width=15)

        target, changed = mgr.update_hover(6, 2)
        assert changed is True
        assert target is not None
        assert target.id == "link_1"
        assert target.hovered is True

        # Move mouse outside
        target_out, changed_out = mgr.update_hover(0, 0)
        assert changed_out is True
        assert target_out is None
        assert mgr._regions[0].hovered is False
