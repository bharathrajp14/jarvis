# career/resume_engine/exporter.py — Multi-Stage Verified Document Export Pipeline
from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from agent.artifacts import get_artifact_manager
from career.resume_engine.models import ResumeSchema, ResumeVersionRecord
from career.resume_engine.renderer import ResumeRenderer
from core.execution.types import ExecutionStatus, VerificationOutcome
from core.execution.verifier import get_universal_verifier

logger = logging.getLogger("JARVIS.ResumeExporter")

_DEFAULT_RESUME_DIR = Path(__file__).resolve().parent.parent.parent / "workspace" / "Resumes"


class ResumeExportPipeline:
    """
    Authoritative Multi-Stage Verified Export Pipeline for Career Documents.
    
    Stages:
    1. CREATE       - Render target formats (DOCX, PDF, HTML)
    2. EXISTS       - Verify file presence on host disk
    3. NON_ZERO     - Verify file byte size > min_size
    4. FORMAT_VALID - Verify file headers & magic numbers
    5. PARSE        - Parse document body (paragraphs, page tree, HTML DOM)
    6. CONTENT      - Check that candidate name and core sections are present
    7. REGISTER     - Export into host ArtifactManager with SHA-256 integrity hash
    8. VERIFY       - Run UniversalVerifier for final seal of authenticity
    """

    def __init__(self, output_dir: Optional[Path | str] = None):
        self.output_dir = Path(output_dir) if output_dir else _DEFAULT_RESUME_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verifier = get_universal_verifier()
        self.artifact_mgr = get_artifact_manager()

    def export_all_formats(
        self,
        resume: ResumeSchema,
        base_name: Optional[str] = None,
        task_id: str = "career_export",
    ) -> Dict[str, Any]:
        """
        Render and physically verify DOCX, PDF, and HTML versions of the resume.
        Returns a verified bundle report.
        """
        clean_title = re.sub(r'[^\w\-]', '_', base_name or resume.title)
        html_path = self.output_dir / f"{clean_title}.html"
        docx_path = self.output_dir / f"{clean_title}.docx"
        pdf_path = self.output_dir / f"{clean_title}.pdf"

        results: Dict[str, Any] = {
            "html": {"path": str(html_path), "verified": False, "details": ""},
            "docx": {"path": str(docx_path), "verified": False, "details": ""},
            "pdf": {"path": str(pdf_path), "verified": False, "details": ""},
            "all_verified": False,
            "artifact_records": [],
        }

        # ── 1. Render HTML ───────────────────────────────────────────────────
        try:
            html_content = ResumeRenderer.render_html(resume)
            html_path.write_text(html_content, encoding="utf-8")
            v_html = self.verifier.verify_document(html_path)
            if v_html.verified:
                results["html"]["verified"] = True
                results["html"]["details"] = v_html.evidence
                art_rec = self.artifact_mgr.register_host_artifact(html_path, task_id=task_id)
                results["artifact_records"].append(art_rec.to_dict())
            else:
                results["html"]["details"] = v_html.details
        except Exception as e:
            results["html"]["details"] = f"HTML export error: {e}"

        # ── 2. Render DOCX ───────────────────────────────────────────────────
        try:
            ResumeRenderer.render_docx(resume, docx_path)
            v_docx = self.verifier.verify_document(docx_path)
            if v_docx.verified:
                results["docx"]["verified"] = True
                results["docx"]["details"] = v_docx.evidence
                art_rec = self.artifact_mgr.register_host_artifact(docx_path, task_id=task_id)
                results["artifact_records"].append(art_rec.to_dict())
            else:
                results["docx"]["details"] = v_docx.details
        except Exception as e:
            results["docx"]["details"] = f"DOCX export error: {e}"

        # ── 3. Render PDF ────────────────────────────────────────────────────
        try:
            ResumeRenderer.render_pdf(resume, pdf_path)
            v_pdf = self.verifier.verify_document(pdf_path)
            if v_pdf.verified:
                results["pdf"]["verified"] = True
                results["pdf"]["details"] = v_pdf.evidence
                art_rec = self.artifact_mgr.register_host_artifact(pdf_path, task_id=task_id)
                results["artifact_records"].append(art_rec.to_dict())
            else:
                results["pdf"]["details"] = v_pdf.details
        except Exception as e:
            results["pdf"]["details"] = f"PDF export error: {e}"

        # Overall Status
        results["all_verified"] = all(
            results[fmt]["verified"] for fmt in ("html", "docx", "pdf")
        )

        logger.info(
            f"📦 Verified Resume Export Complete: '{clean_title}' (All Verified: {results['all_verified']})"
        )
        return results
