# career/application_engine/package_builder.py — Application Package Generator
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.artifacts import get_artifact_manager
from ..cover_letter.generator import CoverLetterGenerator
from ..models import ApplicationPackage, CareerProfile, JobPosting
from ..resume_engine.exporter import ResumeExportPipeline
from ..resume_engine.models import TemplateType, ThemeConfig
from ..resume_engine.tailoring import ResumeTailoringEngine

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.PackageBuilder")

_DEFAULT_APP_DIR = paths.CAREER_DIR / "applications"


class ApplicationPackageBuilder:
    """
    Constructs a comprehensive, verified Application Package bundle:
    - Tailored Resume (DOCX, PDF, HTML)
    - Fact-grounded Cover Letter (PDF, Text)
    - Structured Application Answers (JSON)
    - Snapshot Job Description (HTML)
    - Full Lifecycle Metadata Manifest (JSON)
    """

    def __init__(self, base_dir: Optional[Path | str] = None):
        self.base_dir = Path(base_dir) if base_dir else _DEFAULT_APP_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.exporter = ResumeExportPipeline()
        self.artifact_mgr = get_artifact_manager()

    def build_package(
        self,
        profile: CareerProfile,
        job: JobPosting,
        answers: Optional[Dict[str, Any]] = None,
        template_id: TemplateType = TemplateType.ATS_CLASSIC,
        theme: Optional[ThemeConfig] = None,
    ) -> ApplicationPackage:
        """Assembles and verifies complete deliverable package for job application."""
        pkg_id = f"pkg_{job.company.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        pkg_dir = self.base_dir / pkg_id
        pkg_dir.mkdir(parents=True, exist_ok=True)

        clean_co = re.sub(r'[^\w\-]', '_', job.company)
        clean_role = re.sub(r'[^\w\-]', '_', job.title)

        # 1. Tailor and Export Resume
        tailored_resume, _ = ResumeTailoringEngine.tailor_resume(
            profile=profile,
            job_description=job.description,
            target_role=job.title,
            company_name=job.company,
            job_id=job.job_id,
            template_id=template_id,
            theme=theme,
        )

        export_report = self.exporter.export_all_formats(
            resume=tailored_resume,
            base_name=f"{profile.contact.full_name.replace(' ', '_')}_{clean_co}_{clean_role}",
            task_id=pkg_id,
        )

        resume_docx = export_report["docx"]["path"] if export_report["docx"]["verified"] else ""
        resume_pdf = export_report["pdf"]["path"] if export_report["pdf"]["verified"] else ""
        resume_html = export_report["html"]["path"] if export_report["html"]["verified"] else ""

        # 2. Generate Cover Letter
        cover_text = CoverLetterGenerator.generate(profile=profile, job=job)
        cover_txt_file = pkg_dir / "cover_letter.txt"
        cover_txt_file.write_text(cover_text, encoding="utf-8")

        cover_pdf_file = pkg_dir / "cover_letter.pdf"
        try:
            CoverLetterGenerator.export_pdf(cover_text, cover_pdf_file)
            cover_pdf_path = str(cover_pdf_file)
            self.artifact_mgr.register_host_artifact(cover_pdf_file, task_id=pkg_id)
        except Exception as e:
            logger.debug(f"Cover letter PDF generation fallback: {e}")
            cover_pdf_path = ""

        # 3. Serialize Answers JSON
        answers_payload = answers or {}
        answers_file = pkg_dir / "answers.json"
        answers_file.write_text(json.dumps(answers_payload, indent=2), encoding="utf-8")

        # 4. Save Job Description Snapshot
        jd_file = pkg_dir / "job_description.html"
        jd_html = f"""<!DOCTYPE html>
<html>
<head><title>{job.title} at {job.company}</title><style>body{{font-family: sans-serif; padding: 20px; line-height: 1.5;}}</style></head>
<body>
    <h1>{job.title}</h1>
    <h2>{job.company} — {job.location} ({job.remote_type})</h2>
    <p><strong>Application URL:</strong> <a href="{job.application_url}">{job.application_url}</a></p>
    <p><strong>Discovered:</strong> {time.ctime(job.discovered_at)}</p>
    <hr>
    <div>{job.description}</div>
</body>
</html>"""
        jd_file.write_text(jd_html, encoding="utf-8")

        # 5. Save Package Manifest
        pkg = ApplicationPackage(
            package_id=pkg_id,
            job_id=job.job_id,
            company=job.company,
            role_title=job.title,
            resume_docx_path=resume_docx,
            resume_pdf_path=resume_pdf,
            resume_html_path=resume_html,
            cover_letter_pdf_path=cover_pdf_path,
            cover_letter_text=cover_text,
            answers_json_path=str(answers_file),
            answers_payload=answers_payload,
            job_description_html_path=str(jd_file),
            created_at=time.time(),
        )

        manifest_file = pkg_dir / "application_metadata.json"
        manifest_file.write_text(json.dumps(pkg.to_dict(), indent=2), encoding="utf-8")
        self.artifact_mgr.register_host_artifact(manifest_file, task_id=pkg_id)

        logger.info(f"📦 Complete Application Package assembled: [{pkg_id}] for {job.company}")
        return pkg
