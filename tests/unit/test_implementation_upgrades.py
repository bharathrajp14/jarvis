# tests/test_implementation_upgrades.py — Unit Tests for Next-Phase Upgrades
"""
Verification tests for:
- Pruned tool prompt block token reduction
- CDP Browser DOM Bridge availability and graph structure
- Core compat backend imports
"""
from __future__ import annotations

import logging
import pytest
from tools.registry import get_tool_prompt_block, get_pruned_tool_prompt_block
from vision.dom_bridge import get_cdp_bridge
from core.compat import GeminiBackend

logger = logging.getLogger(__name__)


def test_tool_prompt_pruning():
    """Verify tool prompt pruning reduces token schema block length."""
    full_prompt = get_tool_prompt_block()
    pruned_prompt = get_pruned_tool_prompt_block("open brave browser and search news")

    logger.info(f"\n[Test] Full Prompt Length: {len(full_prompt)} chars | Pruned Prompt Length: {len(pruned_prompt)} chars")
    assert len(pruned_prompt) < len(full_prompt), "Pruned tool prompt block should be significantly shorter"


def test_cdp_dom_bridge_init():
    """Verify CDP Bridge instantiates and checks debug availability safely."""
    bridge = get_cdp_bridge()
    available = bridge.is_browser_debugging_available()
    logger.debug(f"\n[Test] Browser Remote Debugging Available: {available}")
    assert isinstance(available, bool)


def test_compat_backend_import():
    """Verify core.compat re-exports backends cleanly."""
    assert GeminiBackend is not None, "GeminiBackend failed to re-export from core.compat"


if __name__ == "__main__":
    test_tool_prompt_pruning()
    test_cdp_dom_bridge_init()
    test_compat_backend_import()
    logger.info("\n✅ All Implementation Upgrade Tests Passed!")
