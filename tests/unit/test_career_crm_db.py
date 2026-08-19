"""Unit tests for Career CRM SQLite WAL Database."""

from __future__ import annotations

import pytest

from brjarvis.career.crm.database import get_career_crm_db
from brjarvis.career.models import Application, ApplicationStatus


@pytest.mark.unit
def test_career_crm_db_crud():
    """Verify application creation, lookup, and state transition in CRM database."""
    db = get_career_crm_db()
    app = Application(
        application_id="APP-TEST01",
        company="Anthropic",
        job_title="AI Systems Architect",
        application_status=ApplicationStatus.SUBMITTED,
        match_score=92.5,
    )
    db.save_application(app)
    saved = db.get_application("APP-TEST01")
    assert saved is not None
    assert saved.company == "Anthropic"
    assert saved.application_status == ApplicationStatus.SUBMITTED

    # Update status to INTERVIEW_SCHEDULED and save
    saved.application_status = ApplicationStatus.INTERVIEW_SCHEDULED
    db.save_application(saved)
    updated = db.get_application("APP-TEST01")
    assert updated is not None
    assert updated.application_status == ApplicationStatus.INTERVIEW_SCHEDULED
