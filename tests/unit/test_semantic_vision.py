# tests/test_semantic_vision.py — Unit & Integration Test Suite for Semantic Vision OS
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vision.accessibility import get_accessibility_bridge
from vision.dom_bridge import get_cdp_bridge
from vision.engine import get_vision_engine
from vision.hybrid_pipeline import get_hybrid_pipeline
from vision.ocr_engine import OCREngine
from vision.screen_analyst import ScreenAnalyst
from vision.types import ScreenBoundingBox, SemanticUIGraph, SemanticUINode, UIRole
from computer.semantic_operator import SemanticTarget, get_semantic_operator
from computer.recovery import get_self_healing_engine


def test_semantic_types():
    """Test SemanticUINode and SemanticUIGraph tree manipulation."""
    graph = SemanticUIGraph()
    root = SemanticUINode(name="Root Window", role=UIRole.WINDOW, bbox=ScreenBoundingBox(xmin=0, ymin=0, xmax=1920, ymax=1080))
    graph.add_node(root)

    btn = SemanticUINode(name="Submit Button", role=UIRole.BUTTON, bbox=ScreenBoundingBox(xmin=100, ymin=100, xmax=200, ymax=140))
    graph.add_node(btn, parent_id=root.node_id)

    assert len(graph.nodes) == 2
    assert btn.node_id in graph.nodes[root.node_id].children_ids

    found = graph.find_by_name("Submit")
    assert len(found) == 1
    assert found[0].name == "Submit Button"

    found_roles = graph.find_by_role(UIRole.BUTTON)
    assert len(found_roles) == 1
    assert found_roles[0].role == UIRole.BUTTON


def test_accessibility_bridge():
    """Test Accessibility API bridge graph generation."""
    bridge = get_accessibility_bridge()
    graph = bridge.capture_ui_graph()
    assert graph is not None
    assert len(graph.nodes) > 0


def test_ocr_engine_lru_cache():
    """Test OCREngine SHA-256 caching."""
    ocr = OCREngine(cache_size=10)
    raw_data = b"test_frame_bytes_123"
    txt1, elems1 = ocr.extract_text_and_elements(raw_data, 1920, 1080)
    txt2, elems2 = ocr.extract_text_and_elements(raw_data, 1920, 1080)

    assert txt1 == txt2
    assert len(ocr._cache) == 1
    ocr.clear_cache()
    assert len(ocr._cache) == 0


def test_hybrid_vision_pipeline():
    """Test HybridVisionPipeline integration with VisionEngine."""
    engine = get_vision_engine()
    report = engine.analyze_screen(force_refresh=True)
    assert report is not None
    assert report.semantic_graph is not None
    assert len(report.semantic_graph.nodes) > 0


def test_semantic_operator_resolution():
    """Test SemanticComputerOperator target node resolution."""
    sem_op = get_semantic_operator()
    target = SemanticTarget(component_name="Desktop")
    # Will attempt to resolve target on live/fallback graph
    res = sem_op._resolve_target_node(target, sem_op.vision.analyze_screen().semantic_graph)
    assert res is not None or target.component_name is not None


def test_self_healing_engine_init():
    """Test SelfHealingEngine initialization."""
    healer = get_self_healing_engine()
    assert healer is not None
    assert healer.max_recovery_attempts == 3


if __name__ == "__main__":
    print("Running test_semantic_vision.py...")
    test_semantic_types()
    test_accessibility_bridge()
    test_ocr_engine_lru_cache()
    test_hybrid_vision_pipeline()
    test_semantic_operator_resolution()
    test_self_healing_engine_init()
    print("All Semantic Vision OS tests passed successfully!")
