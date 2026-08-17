# core/terminal/viewport.py — Virtualized Viewport & Scroll Manager for BR JARVIS MK41
"""
Virtualized Transcript Viewport & Scroll Manager.
Maintains scroll offset, overscan buffer, line-by-line wheel scrolling,
auto-follow state (automatically disabled when scrolling up, resumed at bottom),
and compact scrollbar rendering.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger("JARVIS.Viewport")


@dataclass
class ViewportRange:
    """Calculated visible line range for virtual rendering."""
    start_index: int = 0
    end_index: int = 0
    total_lines: int = 0
    scroll_offset: int = 0
    is_at_bottom: bool = True


class ScrollManager:
    """
    Controls virtual viewport scrolling and auto-follow behavior.
    """

    def __init__(self, scroll_speed: int = 3, overscan: int = 5):
        self.scroll_speed: int = max(1, min(10, scroll_speed))
        self.overscan: int = overscan
        self.scroll_offset: int = 0               # 0 = Scrolled to the top, >0 = offset down
        self.auto_follow: bool = True              # When True, viewport follows newest bottom lines
        self.content_height: int = 0
        self.viewport_height: int = 24

    def update_dimensions(self, content_height: int, viewport_height: int) -> None:
        """Update total content line count and visible viewport line count."""
        self.content_height = max(0, content_height)
        self.viewport_height = max(1, viewport_height)

        max_offset = max(0, self.content_height - self.viewport_height)

        if self.auto_follow:
            self.scroll_offset = max_offset
        else:
            # Clamp offset within valid bounds
            self.scroll_offset = max(0, min(self.scroll_offset, max_offset))

            # If user reached bottom, resume auto-follow
            if self.scroll_offset >= max_offset:
                self.auto_follow = True

    def scroll_up(self, lines: int = 0) -> None:
        """Scroll up by lines or default scroll_speed. Disables auto-follow."""
        delta = lines or self.scroll_speed
        self.auto_follow = False
        self.scroll_offset = max(0, self.scroll_offset - delta)

    def scroll_down(self, lines: int = 0) -> None:
        """Scroll down by lines or default scroll_speed."""
        delta = lines or self.scroll_speed
        max_offset = max(0, self.content_height - self.viewport_height)
        self.scroll_offset = min(max_offset, self.scroll_offset + delta)

        if self.scroll_offset >= max_offset:
            self.auto_follow = True

    def scroll_page_up(self) -> None:
        """Scroll up by one full viewport page."""
        self.scroll_up(lines=max(1, self.viewport_height - 2))

    def scroll_page_down(self) -> None:
        """Scroll down by one full viewport page."""
        self.scroll_down(lines=max(1, self.viewport_height - 2))

    def scroll_to_top(self) -> None:
        """Scroll to the very beginning of transcript."""
        self.auto_follow = False
        self.scroll_offset = 0

    def scroll_to_bottom(self) -> None:
        """Scroll to bottom and re-enable auto-follow."""
        max_offset = max(0, self.content_height - self.viewport_height)
        self.scroll_offset = max_offset
        self.auto_follow = True

    def get_visible_range(self) -> ViewportRange:
        """Compute the virtual visible slice of lines including overscan."""
        max_offset = max(0, self.content_height - self.viewport_height)
        is_bottom = (self.scroll_offset >= max_offset)

        start = max(0, self.scroll_offset - self.overscan)
        end = min(self.content_height, self.scroll_offset + self.viewport_height + self.overscan)

        return ViewportRange(
            start_index=start,
            end_index=end,
            total_lines=self.content_height,
            scroll_offset=self.scroll_offset,
            is_at_bottom=is_bottom,
        )

    def render_scrollbar(self, height: int) -> List[str]:
        """
        Produce a compact 1-column scrollbar track.
        Uses blocks: █ (thumb), ░ (track).
        """
        if height <= 0:
            return []

        if self.content_height <= height:
            return [" "] * height

        max_offset = max(1, self.content_height - self.viewport_height)
        fraction = min(1.0, max(0.0, self.scroll_offset / max_offset))

        thumb_size = max(1, int(height * (self.viewport_height / max(1, self.content_height))))
        thumb_start = int((height - thumb_size) * fraction)
        thumb_end = thumb_start + thumb_size

        bar = []
        for i in range(height):
            if thumb_start <= i < thumb_end:
                bar.append("█")
            else:
                bar.append("░")
        return bar
