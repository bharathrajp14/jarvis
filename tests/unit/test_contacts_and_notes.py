"""Unit tests for Contact Tools and Document Generation."""
from __future__ import annotations

import pytest
from brjarvis.tools.doc_tools import document_creator
from brjarvis.tools.whatsapp_tools import tool_manage_whatsapp_contacts


@pytest.mark.unit
def test_manage_whatsapp_contacts():
    """Verify adding and listing whatsapp contacts via tool interface."""
    res_add = tool_manage_whatsapp_contacts({"action": "add", "name": "Sarah Connor", "phone": "+15550142"})
    assert "Sarah" in res_add or "saved" in res_add.lower() or "success" in res_add.lower()

    res_list = tool_manage_whatsapp_contacts({"action": "list"})
    assert "Sarah" in res_list or "CONTACTS" in res_list


@pytest.mark.unit
def test_document_creator(temp_workspace):
    """Verify creating a markdown document in the workspace via document_creator."""
    params = {
        "title": "Quantum Architecture",
        "subtitle": "Specification v1.0",
        "author": "BR JARVIS Core",
        "content": "Autonomous System is Fully Operational.",
        "format": "md",
        "auto_open": False
    }
    res = document_creator(params)
    assert "Quantum_Architecture.md" in str(res) or "created" in str(res).lower() or "success" in str(res).lower()
