# tests/test_intent_whatsapp.py — Zero-Token WhatsApp Intent Routing Unit Tests
"""
Unit tests verifying zero-token deterministic intent routing for WhatsApp voice commands.
"""
from __future__ import annotations

import pytest
from core.intent_engine import DeterministicIntentEngine


def test_whatsapp_intent_say_to_appa(monkeypatch):
    res = DeterministicIntentEngine.parse_and_execute("Say hello to appa in watsapp...")
    assert res is not None
    assert res["executed"] is True



def test_whatsapp_intent_send_hi_to_mom(monkeypatch):
    res = DeterministicIntentEngine.parse_and_execute("Send hi to mom on whatsapp")
    assert res is not None
    assert res["executed"] is True



def test_whatsapp_intent_colon_format(monkeypatch):
    res = DeterministicIntentEngine.parse_and_execute("WhatsApp Dharani: Meeting at 5pm")
    assert res is not None
    assert res["executed"] is True

