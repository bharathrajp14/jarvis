# tests/test_relationship_resolution.py — Automated Unit Tests for Relationship Alias Resolution
"""
Unit tests for multilingual relationship alias resolution ("Appa", "Amma", "Dad", "Mom")
across UnifiedContactStore, WhatsAppAutomation, and SmartEmailSender.
"""
from __future__ import annotations

import pytest
from memory.contact_manager import UnifiedContactStore
from actions.whatsapp_automation import WhatsAppAutomation
from actions.smart_email_sender import SmartEmailSender


@pytest.fixture
def relationship_store(tmp_path):
    enc_path = tmp_path / "test_rel.enc"
    legacy_path = tmp_path / "test_rel.json"
    store = UnifiedContactStore(storage_path=enc_path, legacy_path=legacy_path)
    
    # Add test family contacts
    store.add_contact(name="Father", phone_number="+919876543210", email="father@example.com", aliases=["Appa", "Dad"], is_important=True)
    store.add_contact(name="Mother", phone_number="+919876543211", email="mother@example.com", aliases=["Amma", "Mom"], is_important=True)
    store.add_contact(name="Dharani Brother", phone_number="+919876543212", email="bro@example.com", aliases=["Bro", "Bhaiya"])
    return store


def test_contact_store_relationship_resolution(relationship_store):
    # Test Appa resolution
    appa = relationship_store.resolve_name("Appa")
    assert appa is not None
    assert appa["phone_number"] == "+919876543210"

    # Test Dad resolution
    dad = relationship_store.resolve_name("dad")
    assert dad is not None
    assert dad["name"] == "Father"

    # Test Amma resolution
    amma = relationship_store.resolve_name("Amma")
    assert amma is not None
    assert amma["phone_number"] == "+919876543211"

    # Test Mom resolution
    mom = relationship_store.resolve_name("mom")
    assert mom is not None
    assert mom["name"] == "Mother"


def test_whatsapp_recipient_resolution(monkeypatch, relationship_store):
    # Patch get_contact_store to return our test store
    monkeypatch.setattr("memory.contact_manager.get_contact_store", lambda: relationship_store)
    
    wa = WhatsAppAutomation()
    name, phone = wa.resolve_recipient("appa")
    assert name in ("Father", "Appa")
    assert phone == "+919876543210"

    name_mom, phone_mom = wa.resolve_recipient("Amma")
    assert phone_mom == "+919876543211"


def test_email_recipient_resolution(monkeypatch, relationship_store):
    monkeypatch.setattr("memory.contact_manager.get_contact_store", lambda: relationship_store)
    
    es = SmartEmailSender()
    name, email = es.resolve_recipient("appa")
    assert email == "father@example.com"
