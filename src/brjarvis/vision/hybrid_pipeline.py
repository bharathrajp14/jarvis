# vision/hybrid_pipeline.py — Master 7-Tier Hybrid Vision Pipeline for JARVIS MK37
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from .accessibility import get_accessibility_bridge
from .dom_bridge import get_cdp_bridge
from .ocr_engine import OCREngine
from .screen_analyst import ScreenAnalyst
from .types import ScreenBoundingBox, SemanticUIGraph, SemanticUINode, UIRole

logger = logging.getLogger("JARVIS.HybridVisionPipeline")


class HybridVisionPipeline:
    """
    Master 7-Tier Hybrid Vision Pipeline combining Accessibility APIs, DOM trees,
    fast OCR, and VLM fallback to construct a complete SemanticUIGraph.
    """

    def __init__(self):
        self.accessibility = get_accessibility_bridge()
        self.cdp = get_cdp_bridge()
        self.analyst = ScreenAnalyst()
        self.ocr = OCREngine()

    def process_screen(
        self, raw_bytes: bytes, width: int, height: int, frame_hash: int
    ) -> SemanticUIGraph:
        """Construct a unified SemanticUIGraph from the fastest available vision sources."""
        # 1. Tier 1: Accessibility APIs (instant native control tree)
        graph = self.accessibility.capture_ui_graph()

        # 2. Tier 2: Browser DOM Bridge if debugging port is active
        if self.cdp.is_browser_debugging_available():
            dom_graph = self.cdp.capture_dom_graph()
            if dom_graph and dom_graph.root_id:
                # Merge DOM root under active window
                dom_root = dom_graph.nodes[dom_graph.root_id]
                graph.add_node(dom_root, parent_id=graph.root_id)

        # 3. Tier 5: Fast OCR & UI element locator for candidate text regions
        ocr_text, elements = self.ocr.extract_text_and_elements(raw_bytes, width, height)

        for elem in elements:
            # Map DetectedUIElement into SemanticUINode
            node = SemanticUINode(
                name=elem.label or elem.text or "UI Element",
                value=elem.text,
                role=UIRole.BUTTON if elem.element_type.value == "BUTTON" else UIRole.TEXTBOX,
                bbox=elem.bbox,
                confidence=elem.confidence,
                source_tier="ocr_local",
            )
            graph.add_node(node, parent_id=graph.root_id)

        return graph


_global_hybrid_pipeline: Optional[HybridVisionPipeline] = None


def get_hybrid_pipeline() -> HybridVisionPipeline:
    global _global_hybrid_pipeline
    if _global_hybrid_pipeline is None:
        _global_hybrid_pipeline = HybridVisionPipeline()
    return _global_hybrid_pipeline
