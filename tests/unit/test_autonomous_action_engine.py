# tests/unit/test_autonomous_action_engine.py — Unit tests for ActionVerifier & Action Engine
from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest

from agent.verifier import ActionVerifier, VerificationStatus, FileVerifier, ApplicationVerifier
from agent.stage_decomposer import StageDecomposer, StageCapability
from tools.system_diagnostic_tool import check_tool_health, run_safe_self_test
from orchestrator.core import _synthesize_evidence_summary


def test_file_verifier_created_and_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "test_artifact.txt"
        p.write_text("JARVIS Autonomous Verification Test 2026", encoding="utf-8")

        res1 = ActionVerifier.verify_file_created(str(p))
        assert res1.verified is True
        assert res1.status == VerificationStatus.SUCCESS_VERIFIED

        res2 = ActionVerifier.verify_file_content(str(p), expected_substrings=["Autonomous Verification"])
        assert res2.verified is True
        assert res2.status == VerificationStatus.SUCCESS_VERIFIED

        res_missing = ActionVerifier.verify_file_created(str(Path(tmpdir) / "nonexistent.txt"))
        assert res_missing.verified is False
        assert res_missing.status == VerificationStatus.FAILED


def test_docx_parse_verification():
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / "test_doc.docx"
        from tools.doc_tools import document_creator
        document_creator({
            "title": "Unit Test Document",
            "content": "# Heading\n\nVerified paragraph content.\n\n| Col1 | Col2 |\n| --- | --- |\n| A | B |",
            "filename": str(docx_path),
            "format": "docx",
            "auto_open": False,
        })

        res = ActionVerifier.verify_file_parsed(str(docx_path))
        assert res.verified is True
        assert res.status == VerificationStatus.SUCCESS_VERIFIED
        assert "parsed successfully" in res.evidence


def test_stage_decomposer_dynamic():
    prompt = "Analyze OpenClaw and BR JARVIS project, compare architectures, create a comparison document in docx, and open it."
    stages = StageDecomposer.decompose(prompt)

    stage_names = [s.name for s in stages]
    assert any("Research" in s for s in stage_names)
    assert any("Repository" in s for s in stage_names)
    assert any("Compar" in s for s in stage_names)
    assert any("Document" in s for s in stage_names)
    assert any("Verification" in s for s in stage_names)
    assert any("Launch" in s for s in stage_names)


def test_tool_health_and_self_test():
    health = check_tool_health()
    assert "DOCX Generator (python-docx)" in health
    assert "Action Verifier Suite" in health
    assert health["Action Verifier Suite"]["status"] == "READY"

    self_test_res = run_safe_self_test()
    assert len(self_test_res["passed"]) >= 3
    assert len(self_test_res["failed"]) == 0


def test_evidence_summary_generation():
    fake_history = [
        {"tool_name": "web_search", "result": "[{'title': 'OpenClaw Documentation'}]"},
        {"tool_name": "create_word_document", "result": "Created 'workspace/Documents/test.docx' (4,000 chars)"},
    ]
    summary = _synthesize_evidence_summary(fake_history, "Test prompt")
    assert "Completed operations using web_search, create_word_document" in summary
    assert "web_search" in summary
    assert "create_word_document" in summary
