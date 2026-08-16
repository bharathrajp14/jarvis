# tests/unit/test_career_resume_engine.py — Unit Tests for Resume Engine, Templates & Exporter
import pytest
from pathlib import Path
from career.models import CareerProfile
from career.profile_manager import CareerProfileManager
from career.resume_engine import (
    ResumeSchema,
    ResumeRenderer,
    ResumeTailoringEngine,
    ResumeExportPipeline,
    ResumeVersionManager,
    TemplateType,
    list_templates,
)


@pytest.fixture
def sample_profile():
    mgr = CareerProfileManager()
    return mgr.get_profile()


def test_list_all_ten_templates():
    tmpls = list_templates()
    assert len(tmpls) == 10
    template_ids = [t["template_id"] for t in tmpls]
    for expected in [
        "executive", "modern_minimal", "ats_classic", "technical_engineer",
        "developer", "fresh_graduate", "startup_product", "ai_data",
        "cybersecurity", "compact_one_page"
    ]:
        assert expected in template_ids


def test_resume_html_rendering(sample_profile):
    schema = ResumeRenderer.schema_from_profile(sample_profile, template_id=TemplateType.ATS_CLASSIC)
    html = ResumeRenderer.render_html(schema)
    assert "<!DOCTYPE html>" in html
    assert schema.full_name in html
    assert "Professional Summary" in html


def test_resume_tailoring_and_diff(sample_profile):
    jd = "Seeking Senior AI Engineer with deep experience in Python, Playwright, ChromaDB, and high-concurrency systems."
    tailored_schema, diff = ResumeTailoringEngine.tailor_resume(
        profile=sample_profile,
        job_description=jd,
        target_role="Senior AI Engineer",
        company_name="Anthropic",
    )
    assert tailored_schema.target_role == "Senior AI Engineer"
    assert "Anthropic" in tailored_schema.summary
    assert len(diff.emphasized_skills) > 0
    assert diff.target_company == "Anthropic"


def test_multi_format_verified_exporter(tmp_path, sample_profile):
    schema = ResumeRenderer.schema_from_profile(sample_profile, template_id=TemplateType.ATS_CLASSIC)
    exporter = ResumeExportPipeline(output_dir=tmp_path)
    res = exporter.export_all_formats(schema, base_name="TestCandidate_Resume")
    
    assert res["all_verified"] is True
    assert Path(res["html"]["path"]).exists()
    assert Path(res["docx"]["path"]).exists()
    assert Path(res["pdf"]["path"]).exists()
    assert Path(res["pdf"]["path"]).stat().st_size > 500


def test_resume_version_manager(tmp_path, sample_profile):
    schema = ResumeRenderer.schema_from_profile(sample_profile)
    ver_mgr = ResumeVersionManager(storage_dir=tmp_path)
    rec = ver_mgr.register_version(resume=schema, provider="native")
    
    assert rec.version_id.startswith("ver_")
    assert rec.resume_id == schema.resume_id
    
    # Retrieve
    loaded = ver_mgr.get_version(rec.version_id)
    assert loaded is not None
    assert loaded.full_name == schema.full_name
