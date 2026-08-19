"""Integration tests for Career OS Pipeline (Scraping -> ATS Scoring -> CRM)."""

from __future__ import annotations

import pytest

from brjarvis.career.ats_engine import ATSEngine
from brjarvis.career.crm.database import CareerCRMDatabase
from brjarvis.career.models import ApplicationRecord, ApplicationStatus
from tests.fixtures.sample_job_descriptions import JOB_DESCRIPTION_SENIOR_AI_BACKEND
from tests.fixtures.sample_resumes import SAMPLE_AI_ENGINEER_RESUME


@pytest.mark.integration
def test_career_os_evaluation_and_crm_pipeline(tmp_path):
    """Verify ATS score feeds directly into Career CRM application record."""
    engine = ATSEngine()
    score_report = engine.evaluate(SAMPLE_AI_ENGINEER_RESUME, JOB_DESCRIPTION_SENIOR_AI_BACKEND)
    assert score_report.total_score >= 60.0

    db_path = tmp_path / "test_career_pipeline.db"
    crm = CareerCRMDatabase(db_path=db_path)

    app = ApplicationRecord(
        application_id="app_int_101",
        company_name="Scale AI",
        job_title="Senior AI Backend Engineer",
        status=ApplicationStatus.MATCHED,
        match_score=score_report.total_score,
    )
    crm.save_application(app)

    saved = crm.get_application("app_int_101")
    assert saved is not None
    assert saved.match_score >= 60.0
    assert saved.status == ApplicationStatus.MATCHED
