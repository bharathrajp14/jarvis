# tests/unit/test_career_crm_state_machine.py — 24-State Deterministic State Machine Unit Tests
import pytest
import time
from career.crm.database import get_career_crm_db
from career.crm.state_machine import ApplicationStateMachine
from career.models import Application, ApplicationStatus, PriorityLevel


@pytest.fixture
def clean_test_application():
    db = get_career_crm_db()
    app_id = f"TEST-APP-{int(time.time()*1000)}"
    app = Application(
        application_id=app_id,
        job_id="job_test_123",
        company="Anthropic PBC",
        job_title="Lead Systems Architect",
        job_url="https://anthropic.com/careers/test",
        source="Greenhouse",
        platform="Greenhouse",
        application_status=ApplicationStatus.DISCOVERED,
        date_discovered=time.strftime("%Y-%m-%d"),
        priority=PriorityLevel.HIGH,
    )
    db.save_application(app)
    yield app


def test_valid_forward_transitions(clean_test_application):
    app = clean_test_application
    app_id = app.application_id

    # 1. DISCOVERED -> SHORTLISTED
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.SHORTLISTED, evidence="Matched profile criteria")
    assert app.application_status == ApplicationStatus.SHORTLISTED

    # 2. SHORTLISTED -> PREPARING
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.PREPARING, evidence="Initiated resume tailoring")
    assert app.application_status == ApplicationStatus.PREPARING

    # 3. PREPARING -> READY_FOR_REVIEW
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.READY_FOR_REVIEW, evidence="Resume and cover letter generated")
    assert app.application_status == ApplicationStatus.READY_FOR_REVIEW

    # 4. READY_FOR_REVIEW -> APPLICATION_OPENED
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.APPLICATION_OPENED, evidence="Opened Greenhouse portal in browser")
    assert app.application_status == ApplicationStatus.APPLICATION_OPENED

    # 5. APPLICATION_OPENED -> SUBMITTED
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.SUBMITTED, evidence="User pressed submit button on portal")
    assert app.application_status == ApplicationStatus.SUBMITTED

    # 6. SUBMITTED -> SUBMISSION_VERIFIED
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.SUBMISSION_VERIFIED, evidence="Received confirmation email", confirmation_id="CONF-99482")
    assert app.application_status == ApplicationStatus.SUBMISSION_VERIFIED
    assert app.confirmation_id == "CONF-99482"

    # 7. SUBMISSION_VERIFIED -> INTERVIEW_SCHEDULED
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.INTERVIEW_SCHEDULED, evidence="Calendar invite received")
    assert app.application_status == ApplicationStatus.INTERVIEW_SCHEDULED

    # 8. INTERVIEW_SCHEDULED -> OFFER_RECEIVED
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.OFFER_RECEIVED, evidence="Offer package emailed")
    assert app.application_status == ApplicationStatus.OFFER_RECEIVED

    # 9. OFFER_RECEIVED -> OFFER_ACCEPTED
    app = ApplicationStateMachine.transition(app_id, ApplicationStatus.OFFER_ACCEPTED, evidence="Signed offer letter confirmed by candidate")
    assert app.application_status == ApplicationStatus.OFFER_ACCEPTED


def test_invalid_transition_rejected(clean_test_application):
    app_id = clean_test_application.application_id

    # DISCOVERED cannot jump directly to OFFER_ACCEPTED
    with pytest.raises(ValueError, match="Cannot advance directly"):
        ApplicationStateMachine.transition(app_id, ApplicationStatus.OFFER_ACCEPTED, evidence="Invalid jump attempt")



def test_immutable_event_store_records_history(clean_test_application):
    db = get_career_crm_db()
    app_id = clean_test_application.application_id

    ApplicationStateMachine.transition(app_id, ApplicationStatus.SHORTLISTED, evidence="Step 1")
    ApplicationStateMachine.transition(app_id, ApplicationStatus.PREPARING, evidence="Step 2")

    events = db.get_events_for_application(app_id)
    assert len(events) >= 2
    assert events[-1].new_state == "PREPARING"
    assert events[-1].evidence == "Step 2"
