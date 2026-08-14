# tests/adversarial/test_fast_path_hostile.py — Hostile Fast-Path & Ambiguity Attack Suite
from __future__ import annotations

import pytest
from core.intent_engine import DeterministicIntentEngine


def test_fast_path_deterministic_inputs_hit():
    """Verify standard unambiguous system commands hit deterministic fast-path immediately."""
    fast_inputs = [
        "open chrome",
        "open notepad",
        "mute",
        "unmute",
        "volume up",
        "volume down",
        "show cpu",
        "ram usage",
        "system status",
        "take screenshot",
        "lock screen",
    ]

    for inp in fast_inputs:
        result = DeterministicIntentEngine.parse_and_execute(inp)
        assert result is not None, f"Expected fast-path hit for: '{inp}'"
        assert isinstance(result, dict)
        assert result.get("executed") is True
        assert len(result.get("result", "")) > 0


def test_fast_path_ambiguous_and_reasoning_inputs_rejected():
    """Ensure ambiguous and cognitive requests are strictly rejected by the fast path."""
    ambiguous_and_reasoning_inputs = [
        "open the thing I used yesterday",
        "make the browser faster",
        "check what's wrong with my computer",
        "why is my cpu high right now?",
        "write a python script to calculate fibonacci",
        "who was the 16th president of the united states?",
        "what did we discuss last tuesday about the project?",
        "summarize the document on my desktop",
        "find all files modified in the last 2 hours and email them to me",
        "plan a trip to Tokyo for next month",
    ]

    for inp in ambiguous_and_reasoning_inputs:
        result = DeterministicIntentEngine.parse_and_execute(inp)
        assert result is None, (
            f"FALSE POSITIVE: Ambiguous/cognitive query '{inp}' entered deterministic fast-path! "
            f"Result was: '{result}'"
        )
