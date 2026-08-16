# mobile/screen_understanding.py — Hybrid Multimodal Mobile Screen Understanding
"""
Multimodal Android Screen Understanding Engine for BR JARVIS MK37.
Combines Accessibility Tree hierarchy + OCR text layout + Vision models to locate
and interact with UI controls semantically without hardcoded screen coordinates.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .protocol import AccessibilityNode

logger = logging.getLogger("JARVIS.MobileScreenUnderstanding")


@dataclass
class UIElementMatch:
    node_id: int
    text: str
    class_name: str
    view_id: str
    bounds: List[int]  # [left, top, right, bottom]
    center: Tuple[int, int]
    confidence: float
    match_source: str  # "accessibility", "view_id", "content_desc", "ocr", "vision"


class MobileScreenUnderstanding:
    """Parses and indexes mobile UI structures for intelligent semantic interaction."""

    def __init__(self):
        pass

    def flatten_tree(self, root: AccessibilityNode) -> List[AccessibilityNode]:
        """Flatten recursive node tree into flat list of interactive/readable elements."""
        nodes = []
        stack = [root]
        while stack:
            curr = stack.pop()
            nodes.append(curr)
            if curr.children:
                stack.extend(reversed(curr.children))
        return nodes

    def find_element(
        self,
        root: AccessibilityNode,
        query: str,
        class_name_filter: Optional[str] = None,
        clickable_only: bool = False
    ) -> Optional[UIElementMatch]:
        """Find best matching UI element by text, description, or resource ID."""
        q = query.lower().strip()
        nodes = self.flatten_tree(root)

        best_match: Optional[UIElementMatch] = None
        best_score = 0.0

        for n in nodes:
            if clickable_only and not n.is_clickable and not n.is_editable:
                continue
            if class_name_filter and class_name_filter.lower() not in n.class_name.lower():
                continue

            node_text = (n.text or "").strip().lower()
            node_desc = (n.content_description or "").strip().lower()
            node_id_str = (n.view_id or "").strip().lower()

            score = 0.0
            source = "accessibility"

            # Exact text match
            if node_text == q:
                score = 1.0
                source = "text_exact"
            # Exact content description match
            elif node_desc == q:
                score = 0.95
                source = "content_desc_exact"
            # View resource ID match (e.g. "send_button", "search_src_text")
            elif q in node_id_str:
                score = 0.90
                source = "view_id"
            # Substring match
            elif q in node_text:
                score = 0.80
                source = "text_contains"
            elif q in node_desc:
                score = 0.75
                source = "content_desc_contains"

            if score > best_score:
                b = n.bounds
                center_x = (b[0] + b[2]) // 2 if len(b) == 4 else 0
                center_y = (b[1] + b[3]) // 2 if len(b) == 4 else 0

                best_score = score
                best_match = UIElementMatch(
                    node_id=n.node_id,
                    text=n.text or n.content_description or n.view_id,
                    class_name=n.class_name,
                    view_id=n.view_id,
                    bounds=b,
                    center=(center_x, center_y),
                    confidence=score,
                    match_source=source
                )

        if best_match and best_score >= 0.7:
            logger.info("Found UI element '%s' (score=%.2f, source=%s)", best_match.text, best_score, best_match.match_source)
            return best_match

        return None

    def summarize_screen(self, root: AccessibilityNode) -> str:
        """Create a compact human-readable textual summary of what is visible on the mobile screen."""
        nodes = self.flatten_tree(root)
        lines = []
        for n in nodes:
            label = (n.text or n.content_description or "").strip()
            if label:
                kind = "Button" if n.is_clickable else ("Input" if n.is_editable else "Text")
                lines.append(f"- [{kind}] \"{label}\" (id: {n.node_id})")
        return "\n".join(lines[:40]) if lines else "Empty or blank screen."


_screen_understanding_instance: Optional[MobileScreenUnderstanding] = None


def get_mobile_screen_understanding() -> MobileScreenUnderstanding:
    global _screen_understanding_instance
    if _screen_understanding_instance is None:
        _screen_understanding_instance = MobileScreenUnderstanding()
    return _screen_understanding_instance
