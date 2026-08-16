"""
Unit tests for BR JARVIS Executive Document Generator Engine (doc_tools.py).
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from brjarvis.tools.doc_tools import (
    document_creator,
    create_word_document,
    create_pdf_document,
    generate_walkthrough,
    generate_project_product_analysis,
    _resolve_doc_path,
)
from brjarvis.agent.verifier import ActionVerifier


@pytest.mark.unit
def test_resolve_doc_path_rules():
    """Verify path resolver normalizes paths and avoids duplicated workspace/ segments."""
    # 1. Empty filename defaults under documents dir
    p_default = _resolve_doc_path("", "System Audit Report", "docx")
    assert "System_Audit_Report.docx" in str(p_default)
    assert "workspace/workspace" not in str(p_default).replace("\\", "/").lower()
    assert "documents/documents" not in str(p_default).replace("\\", "/").lower()

    # 2. Workspace relative path with 'workspace/' prefix stripped
    p_ws = _resolve_doc_path("workspace/Reports/Product_Plan.docx", "Product Plan", "docx")
    assert "workspace/workspace" not in str(p_ws).replace("\\", "/").lower()
    assert str(p_ws).replace("\\", "/").endswith("workspace/Reports/Product_Plan.docx")

    # 3. Bare filename placed under documents dir
    p_bare = _resolve_doc_path("financial_summary.pdf", "Financial Summary", "pdf")
    assert str(p_bare).replace("\\", "/").endswith("workspace/documents/financial_summary.pdf") or str(p_bare).replace("\\", "/").endswith("workspace/Documents/financial_summary.pdf")

    # 4. Absolute path preserved
    with tempfile.TemporaryDirectory() as tmp:
        abs_target = Path(tmp) / "custom_doc.html"
        p_abs = _resolve_doc_path(str(abs_target), "Custom", "html")
        assert p_abs == abs_target.resolve()


@pytest.mark.unit
def test_document_creator_docx():
    """Verify creating a publication-grade DOCX document with table, callout, and code block."""
    with tempfile.TemporaryDirectory() as tmp:
        out_file = Path(tmp) / "test_report.docx"
        content = """
# System Architecture

This is an **executive overview** with *high precision* and `0-token` latency optimizations.

> [!NOTE]
> B.R. JARVIS operates local-first with verifiable state tracking.

| Component | Status | Latency |
| --- | --- | --- |
| Kernel | Active | 0ms |
| Router | Active | 1ms |
| Verifier | Active | 2ms |

```python
def verify_kernel():
    return True
```

- High-throughput execution
- Deterministic verification
1. Step one initialization
2. Step two audit execution
"""
        res = document_creator({
            "title": "System Architecture Report",
            "subtitle": "Q3 Technical Briefing",
            "author": "BR JARVIS Core",
            "content": content,
            "filename": str(out_file),
            "format": "docx",
            "cover_page": True,
            "auto_open": False
        })

        assert "SUCCESS_VERIFIED" in res or "Created Executive Document" in res
        assert out_file.exists()
        assert out_file.stat().st_size > 500

        v_res = ActionVerifier.verify_file_parsed(str(out_file))
        assert v_res.verified


@pytest.mark.unit
def test_document_creator_pdf():
    """Verify creating an executive PDF document with tables and callouts."""
    with tempfile.TemporaryDirectory() as tmp:
        out_file = Path(tmp) / "test_report.pdf"
        content = """
# PDF Diagnostic Report

## 1. Executive Summary
- Operational status: **READY**
- Verified multi-layer security

> [!TIP]
> PDF engine uses native vector rendering and UTF-8 typography.

| Metric | Target | Actual |
| --- | --- | --- |
| Memory | < 500MB | 240MB |
| Latency | < 50ms | 12ms |
"""
        res = document_creator({
            "title": "PDF Diagnostic Report",
            "subtitle": "System Audit",
            "author": "BR JARVIS AI",
            "content": content,
            "filename": str(out_file),
            "format": "pdf",
            "auto_open": False
        })

        assert "SUCCESS_VERIFIED" in res or "Created Executive Document" in res
        assert out_file.exists()
        assert out_file.stat().st_size > 500

        # Check PDF header
        with open(out_file, "rb") as f:
            header = f.read(5)
        assert header.startswith(b"%PDF-")

        v_res = ActionVerifier.verify_file_parsed(str(out_file))
        assert v_res.verified


@pytest.mark.unit
def test_document_creator_html():
    """Verify creating a modern Glassmorphism HTML document."""
    with tempfile.TemporaryDirectory() as tmp:
        out_file = Path(tmp) / "test_report.html"
        content = """
# Glassmorphism HTML Report

## Overview
HTML generation provides **responsive web layouts** and *clean styles*.

> [!IMPORTANT]
> Always verify DOM integrity before closing tasks.

| Service | Protocol | Port |
| --- | --- | --- |
| Web UI | HTTP | 8000 |
| Gateway | HTTP | 8045 |

- Clean typography
- Print-ready CSS
"""
        res = document_creator({
            "title": "Glassmorphism HTML Report",
            "subtitle": "Web Interface Specification",
            "author": "BR JARVIS Web Core",
            "content": content,
            "filename": str(out_file),
            "format": "html",
            "auto_open": False
        })

        assert "SUCCESS_VERIFIED" in res
        assert out_file.exists()
        html_txt = out_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_txt
        assert "class='container'" in html_txt
        assert "<table" in html_txt
        assert "class='callout'" in html_txt
        assert "<ul>" in html_txt


@pytest.mark.unit
def test_document_creator_md():
    """Verify creating a clean Markdown document."""
    with tempfile.TemporaryDirectory() as tmp:
        out_file = Path(tmp) / "test_report.md"
        res = document_creator({
            "title": "Markdown Technical Note",
            "subtitle": "Dev Spec",
            "author": "BR JARVIS",
            "content": "This is markdown content.",
            "filename": str(out_file),
            "format": "md",
            "auto_open": False
        })
        assert "SUCCESS_VERIFIED" in res
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Markdown Technical Note" in content
        assert "This is markdown content." in content


@pytest.mark.unit
def test_convenience_tool_wrappers():
    """Verify create_word_document, create_pdf_document, and generate_walkthrough wrappers."""
    with tempfile.TemporaryDirectory() as tmp:
        docx_file = Path(tmp) / "wrapper_test.docx"
        res_word = create_word_document({
            "title": "Word Wrapper Test",
            "content": "# Header\n\nWord wrapper content.",
            "filename": str(docx_file),
            "auto_open": False
        })
        assert "SUCCESS_VERIFIED" in res_word
        assert docx_file.exists()

        pdf_file = Path(tmp) / "wrapper_test.pdf"
        res_pdf = create_pdf_document({
            "title": "PDF Wrapper Test",
            "content": "# Header\n\nPDF wrapper content.",
            "filename": str(pdf_file),
            "auto_open": False
        })
        assert "SUCCESS_VERIFIED" in res_pdf
        assert pdf_file.exists()

        wt_file = Path(tmp) / "walkthrough_test.md"
        res_wt = generate_walkthrough({
            "title": "Document Creator Fix",
            "summary": "Repaired and modernized document creator engine.",
            "changes": "- Fixed path duplication\n- Enhanced DOCX/PDF/HTML formatting",
            "verification": "All unit tests passing.",
            "filename": str(wt_file),
            "auto_open": False
        })
        assert "Generated Walkthrough" in res_wt
        assert wt_file.exists()
