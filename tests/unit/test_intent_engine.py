"""Unit tests for Intent Classification Engine."""
from __future__ import annotations

import pytest
from brjarvis.core.intent_engine import DeterministicIntentEngine


@pytest.mark.unit
def test_deterministic_intent_engine_dedup():
    """Verify deduplication guard prevents immediate duplicate app trigger."""
    assert DeterministicIntentEngine._dedup_check("notepad") is False
    assert DeterministicIntentEngine._dedup_check("notepad") is True


@pytest.mark.unit
def test_deterministic_intent_app_mappings():
    """Verify standard app mappings exist in registry."""
    mappings = DeterministicIntentEngine.APP_MAPPINGS
    assert "excel" in mappings
    assert "word" in mappings
    assert "calculator" in mappings or "calc" in mappings
    assert "vscode" in mappings
