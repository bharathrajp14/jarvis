# core/terminal/hit_test.py — Spatial Hit-Testing & Interactive Regions for BR JARVIS MK41
"""
Spatial Hit-Testing Engine for the Terminal Interaction Layer.
Maps 2D terminal coordinates (x=col, y=row) to semantic InteractiveRegion objects
for clicks, double-clicks, drags, and hover states.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.HitTest")


class RegionType(str, Enum):
    PROMPT = "prompt"
    BUTTON = "button"
    MENU_ITEM = "menu_item"
    LINK = "link"
    FILE_PATH = "file_path"
    TOOL_RESULT = "tool_result"
    COLLAPSIBLE = "collapsible"
    CHECKBOX = "checkbox"
    TAB = "tab"
    STATUS_ITEM = "status_item"
    SCROLLBAR = "scrollbar"


@dataclass
class InteractiveRegion:
    """Represents a clickable or hoverable rectangular bounding box in terminal coordinates."""
    id: str
    region_type: RegionType
    x: int                                      # Left column (0-indexed)
    y: int                                      # Top row (0-indexed)
    width: int                                  # Width in characters
    height: int = 1                             # Height in rows
    priority: int = 10                          # Higher priority captures first in overlaps
    enabled: bool = True
    hovered: bool = False
    action_name: str = ""                       # Semantic action (e.g. "tool:toggle", "link:open")
    action_args: Dict[str, Any] = field(default_factory=dict)
    tooltip: str = ""

    def contains(self, px: int, py: int) -> bool:
        """Check if terminal coordinate (px, py) falls inside this region."""
        if not self.enabled:
            return False
        return (self.x <= px < self.x + self.width) and (self.y <= py < self.y + self.height)


class HitTestManager:
    """
    Manages active interactive regions per frame and dispatches hits.
    """

    def __init__(self):
        self._regions: List[InteractiveRegion] = []
        self._hovered_region_id: Optional[str] = None

    def clear(self) -> None:
        """Clear all registered regions (called before each frame render)."""
        self._regions.clear()

    def register_region(self, region: InteractiveRegion) -> None:
        """Register an interactive region for the current frame."""
        self._regions.append(region)

    def register(
        self,
        region_id: str,
        region_type: RegionType,
        x: int,
        y: int,
        width: int,
        height: int = 1,
        action: str = "",
        args: Optional[Dict[str, Any]] = None,
        priority: int = 10,
        tooltip: str = "",
    ) -> InteractiveRegion:
        """Convenience method to construct and register a region."""
        reg = InteractiveRegion(
            id=region_id,
            region_type=region_type,
            x=x,
            y=y,
            width=max(1, width),
            height=max(1, height),
            action_name=action,
            action_args=args or {},
            priority=priority,
            tooltip=tooltip,
        )
        self.register_region(reg)
        return reg

    def hit_test(self, x: int, y: int) -> Optional[InteractiveRegion]:
        """
        Return the highest-priority interactive region containing (x, y).
        """
        matching = [r for r in self._regions if r.contains(x, y)]
        if not matching:
            return None
        # Sort descending by priority
        matching.sort(key=lambda r: r.priority, reverse=True)
        return matching[0]

    def update_hover(self, x: int, y: int) -> Tuple[Optional[InteractiveRegion], bool]:
        """
        Update hover state based on mouse coordinates.
        Returns (current_hovered_region, has_hover_changed).
        """
        target = self.hit_test(x, y)
        new_id = target.id if target else None
        changed = (new_id != self._hovered_region_id)

        if changed:
            # Unhover previous
            for r in self._regions:
                r.hovered = (r.id == new_id)
            self._hovered_region_id = new_id

        return target, changed
