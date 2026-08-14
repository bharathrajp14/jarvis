# tests/test_stt_variations.py — Unit Tests for STT Voice Variations & Tool Pruning Resilience
"""
Unit tests verifying zero-token execution for spoken STT variations ("hii", missing "to", "watsapp....")
and ensuring send_whatsapp is never pruned out of tool prompt schemas.
"""
from __future__ import annotations

import logging
import pytest
from core.intent_engine import DeterministicIntentEngine
from tools.registry import get_pruned_tool_prompt_block, _import_plugins
import tools.whatsapp_tools

logger = logging.getLogger(__name__)


def test_stt_missing_to_and_double_i(monkeypatch):
    res = DeterministicIntentEngine.parse_and_execute("Say hii dharani in watsapp....")
    assert res is not None
    assert res["executed"] is True



def test_tool_pruning_includes_send_whatsapp_on_stt_watsapp():
    from tools.registry import TOOL_SCHEMAS, _import_plugins
    _import_plugins()
    prompt_block = get_pruned_tool_prompt_block("Say hii dharani in watsapp")
    logger.info("PROMPT BLOCK ENTIRE STRING:\n%s", prompt_block[:500])
    assert "send_whatsapp" in prompt_block
