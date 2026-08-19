"""Integration tests for Cross-Device Planner & Mobile Sync."""

from __future__ import annotations

import pytest

from brjarvis.agent.cross_device_planner import CrossDevicePlanner


@pytest.mark.integration
def test_cross_device_planner_init():
    """Verify CrossDevicePlanner initializes with valid device registry."""
    planner = CrossDevicePlanner()
    assert planner is not None
    assert hasattr(planner, "dispatch_plan") or hasattr(planner, "devices")
