"""Unit tests for 7-Factor ATS Compatibility Scorer."""

from __future__ import annotations

import pytest

from brjarvis.career.ats_engine.scorer import ATSEngine
from brjarvis.career.resume_engine.models import ResumeSchema, SectionConfig
from tests.fixtures.sample_job_descriptions import JOB_DESCRIPTION_SENIOR_AI_BACKEND


@pytest.mark.unit
def test_ats_scorer_strong_match():
    """Verify strong resume matches with high score."""
    resume = ResumeSchema(
        full_name="Bharath Raj",
        target_role="Senior AI Systems Engineer",
        summary="Senior AI Systems Engineer with 8+ years developing multi-agent systems, LLMs, and Python distributed infrastructure.",
        sections=[
            SectionConfig(section_id="summary", title="Summary"),
            SectionConfig(section_id="skills", title="Skills"),
            SectionConfig(section_id="experience", title="Experience"),
            SectionConfig(section_id="projects", title="Projects"),
        ],
        skills=[
            {"name": "Python"},
            {"name": "FastAPI"},
            {"name": "Docker"},
            {"name": "Kubernetes"},
            {"name": "PyTorch"},
        ],
        experience=[
            {
                "title": "Lead AI Engineer",
                "company": "Antigravity",
                "bullets": ["Architected distributed agent workflows."],
            }
        ],
    )
    score_report = ATSEngine.evaluate_resume(resume, JOB_DESCRIPTION_SENIOR_AI_BACKEND)
    assert score_report.overall_score >= 40.0
    assert hasattr(score_report, "keyword_coverage_score")


@pytest.mark.unit
def test_ats_scorer_weak_match():
    """Verify weak resume produces low keyword coverage score."""
    resume = ResumeSchema(
        full_name="Junior Tester",
        target_role="QA Intern",
        summary="Manual testing of web forms.",
        skills=[{"name": "Manual Testing"}, {"name": "MS Word"}],
    )
    score_report = ATSEngine.evaluate_resume(resume, JOB_DESCRIPTION_SENIOR_AI_BACKEND)
    assert score_report.keyword_coverage_score < 40.0
