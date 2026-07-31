# tests/test_intent_whatsapp.py — Zero-Token WhatsApp Intent Routing Unit Tests
"""
Unit tests verifying zero-token deterministic intent routing for WhatsApp voice commands.
"""
from __future__ import annotations

import pytest
from core.intent_engine import DeterministicIntentEngine


def test_whatsapp_intent_say_to_appa(monkeypatch):
    executed_call = {}

    class MockWhatsAppAutomation:
        def send_message(self, recipient: str, message_text: str) -> str:
            executed_call["recipient"] = recipient
            executed_call["message_text"] = message_text
            return f"✅ Opened WhatsApp to send message to {recipient}."

    monkeypatch.setattr("actions.whatsapp_automation.get_whatsapp_automation", lambda: MockWhatsAppAutomation())

    res = DeterministicIntentEngine.parse_and_execute("Say hello to appa in watsapp...")
    assert res is not None
    assert res["executed"] is True
    assert res["intent"] == "whatsapp_send"
    assert executed_call["recipient"] == "appa"
    assert executed_call["message_text"] == "hello"


def test_whatsapp_intent_send_hi_to_mom(monkeypatch):
    executed_call = {}

    class MockWhatsAppAutomation:
        def send_message(self, recipient: str, message_text: str) -> str:
            executed_call["recipient"] = recipient
            executed_call["message_text"] = message_text
            return f"✅ Opened WhatsApp to send message to {recipient}."

    monkeypatch.setattr("actions.whatsapp_automation.get_whatsapp_automation", lambda: MockWhatsAppAutomation())

    res = DeterministicIntentEngine.parse_and_execute("Send hi to mom on whatsapp")
    assert res is not None
    assert res["executed"] is True
    assert res["intent"] == "whatsapp_send"
    assert executed_call["recipient"] == "mom"
    assert executed_call["message_text"] == "hi"


def test_whatsapp_intent_colon_format(monkeypatch):
    executed_call = {}

    class MockWhatsAppAutomation:
        def send_message(self, recipient: str, message_text: str) -> str:
            executed_call["recipient"] = recipient
            executed_call["message_text"] = message_text
            return f"✅ Opened WhatsApp to send message to {recipient}."

    monkeypatch.setattr("actions.whatsapp_automation.get_whatsapp_automation", lambda: MockWhatsAppAutomation())

    res = DeterministicIntentEngine.parse_and_execute("WhatsApp Dharani: Meeting at 5pm")
    assert res is not None
    assert res["executed"] is True
    assert res["intent"] == "whatsapp_send"
    assert executed_call["recipient"].lower() == "dharani"
    assert executed_call["message_text"].lower() == "meeting at 5pm"
