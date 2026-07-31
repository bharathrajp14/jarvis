# tests/test_contact_importer.py — Automated Test Suite for Contacts & File Ingestion
"""
Unit and integration tests for UnifiedContactStore, vCard/CSV parsing,
fuzzy name resolution, and multi-file knowledge ingestion.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from memory.contact_manager import UnifiedContactStore
from actions.file_importer import import_file_to_knowledge


@pytest.fixture
def temp_contact_store(tmp_path):
    enc_path = tmp_path / "test_contacts.enc"
    legacy_path = tmp_path / "test_contacts.json"
    return UnifiedContactStore(storage_path=enc_path, legacy_path=legacy_path)


def test_vcf_import(temp_contact_store):
    vcf_content = """BEGIN:VCARD
VERSION:3.0
FN:Margaret Smith
N:Smith;Margaret;;;
TEL;TYPE=CELL:+15551234567
EMAIL;TYPE=INTERNET:mom@example.com
NICKNAME:Mom
END:VCARD

BEGIN:VCARD
VERSION:3.0
FN:John Doe
N:Doe;John;;;
TEL;TYPE=WORK:+15559876543
EMAIL;TYPE=INTERNET:john.doe@work.com
NICKNAME:Johnny
END:VCARD
"""
    res = temp_contact_store.import_vcf(vcf_content)
    assert res["status"] == "success"
    assert res["imported_new"] == 2

    # Verify fuzzy resolution
    mom_contact = temp_contact_store.resolve_name("Mom")
    assert mom_contact is not None
    assert mom_contact["name"] == "Margaret Smith"
    assert mom_contact["phone_number"] == "+15551234567"
    assert mom_contact["email"] == "mom@example.com"

    john_contact = temp_contact_store.resolve_name("John")
    assert john_contact is not None
    assert john_contact["name"] == "John Doe"
    assert john_contact["phone_number"] == "+15559876543"


def test_csv_import(temp_contact_store):
    csv_content = """Name,Phone,Email,Nickname
Alice Johnson,+15550001111,alice@example.com,Boss
Bob Williams,+15552223333,bob@example.com,Brother
"""
    res = temp_contact_store.import_csv(csv_content)
    assert res["status"] == "success"
    assert res["imported_new"] == 2

    boss = temp_contact_store.resolve_name("Boss")
    assert boss is not None
    assert boss["name"] == "Alice Johnson"

    bob = temp_contact_store.resolve_name("bob")
    assert bob is not None
    assert bob["name"] == "Bob Williams"


def test_primary_vcf_import_path(temp_contact_store):
    res = temp_contact_store.import_primary_vcf()
    assert res["status"] in ("success", "not_found")
    if res["status"] == "success":
        assert res["total_store"] > 0
        assert temp_contact_store.get_important_count() > 0


def test_file_importer(tmp_path):
    doc_path = tmp_path / "project_brief.txt"
    doc_path.write_text("BR JARVIS AI Operating System project brief context for testing.", encoding="utf-8")

    res = import_file_to_knowledge(doc_path)
    assert res["status"] == "success"
    assert res["type"] == "document"
    assert "project_brief.txt" in res["message"]

