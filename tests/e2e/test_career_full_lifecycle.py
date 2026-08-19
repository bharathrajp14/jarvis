"""E2E Test: Full Career OS User Journey."""

from __future__ import annotations

import pytest

from brjarvis.career.ats_engine import ATSEngine
from brjarvis.career.crm.database import CareerCRMDatabase
from brjarvis.career.models import ApplicationRecord, ApplicationStatus
from tests.fixtures.sample_job_descriptions import JOB_DESCRIPTION_SENIOR_AI_BACKEND
from tests.fixtures.sample_resumes import SAMPLE_AI_ENGINEER_RESUME


@pytest.mark.e2e
def test_career_full_lifecycle_journey(tmp_path):
    """Verify Career OS journey: Job Analysis -> ATS Evaluation -> CRM Record -> Status Updates."""
    # 1. Evaluate ATS match
    engine = ATSEngine()
    score_report = engine.evaluate(SAMPLE_AI_ENGINEER_RESUME, JOB_DESCRIPTION_SENIOR_AI_BACKEND)
    assert score_report.total_score >= 60.0

    # 2. Ingest into CRM
    db_file = tmp_path / "lifecycle_crm.db"
    crm = CareerCRMDatabase(db_path=db_file)

    app = ApplicationRecord(
        application_id="app_e2e_999",
        company_name="Scale AI",
        job_title="Senior AI Backend Engineer",
        status=ApplicationStatus.APPLIED,
        match_score=score_report.total_score,
    )
    crm.save_application(app)

    # 3. Transition to Interview and Offer
    crm.update_application_status("app_e2e_999", ApplicationStatus.INTERVIEW)
    assert crm.get_application("app_e2e_999").status == ApplicationStatus.INTERVIEW

    crm.update_application_status("app_e2e_999", ApplicationStatus.OFFER)
    assert crm.get_application("app_e2e_999").status == ApplicationStatus.OFFER
