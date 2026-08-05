# tests/test_multi_channel_intent.py — Unit Tests for Multi-Channel (WhatsApp + Gmail) & Email Intent Engine
"""
Unit tests verifying zero-token multi-channel compound intent routing (WhatsApp + Gmail)
and standalone email/gmail intent parsing.
"""
from __future__ import annotations

import pytest
from core.intent_engine import DeterministicIntentEngine


def test_multi_channel_whatsapp_and_gmail(monkeypatch):
    res = DeterministicIntentEngine.parse_and_execute("Say hi to dharani in watsapp and gmail")
    assert res is None


def test_standalone_email_intent(monkeypatch):
    res = DeterministicIntentEngine.parse_and_execute("Send hello to mom via email")
    assert res is None
