# tests/test_multi_channel_intent.py — Unit Tests for Multi-Channel (WhatsApp + Gmail) & Email Intent Engine
"""
Unit tests verifying zero-token multi-channel compound intent routing (WhatsApp + Gmail)
and standalone email/gmail intent parsing.
"""
from __future__ import annotations

import pytest
from core.intent_engine import DeterministicIntentEngine


def test_multi_channel_whatsapp_and_gmail(monkeypatch):
    wa_calls = {}
    em_calls = {}

    class MockWhatsAppAutomation:
        def send_message(self, recipient: str, message_text: str) -> str:
            wa_calls["recipient"] = recipient
            wa_calls["message_text"] = message_text
            return f"✅ Opened WhatsApp to send message to {recipient}."

    class MockSmartEmailSender:
        def send_email(self, recipient: str, subject: str, body: str) -> str:
            em_calls["recipient"] = recipient
            em_calls["subject"] = subject
            em_calls["body"] = body
            return f"✅ Sent email to {recipient}."

    monkeypatch.setattr("actions.whatsapp_automation.get_whatsapp_automation", lambda: MockWhatsAppAutomation())
    monkeypatch.setattr("actions.smart_email_sender.SmartEmailSender", lambda: MockSmartEmailSender())

    res = DeterministicIntentEngine.parse_and_execute("Say hi to dharani in watsapp and gmail")
    assert res is not None
    assert res["executed"] is True
    assert res["intent"] == "multi_channel_send"
    assert wa_calls["recipient"].lower() == "dharani"
    assert wa_calls["message_text"] == "hi"
    assert em_calls["recipient"].lower() == "dharani"
    assert em_calls["body"] == "hi"


def test_standalone_email_intent(monkeypatch):
    em_calls = {}

    class MockSmartEmailSender:
        def send_email(self, recipient: str, subject: str, body: str) -> str:
            em_calls["recipient"] = recipient
            em_calls["subject"] = subject
            em_calls["body"] = body
            return f"✅ Sent email to {recipient}."

    monkeypatch.setattr("actions.smart_email_sender.SmartEmailSender", lambda: MockSmartEmailSender())

    res = DeterministicIntentEngine.parse_and_execute("Send hello to mom via email")
    assert res is not None
    assert res["executed"] is True
    assert res["intent"] == "email_send"
    assert em_calls["recipient"].lower() == "mom"
    assert em_calls["body"] == "hello"
