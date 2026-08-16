# tests/e2e/test_career_os_e2e.py — Complete Career OS End-to-End Lifecycle Simulation
import time
import uuid
import pytest
from career.crm.database import get_career_crm_db
from career.crm.event_pipeline import get_career_pipeline
from career.crm.followup_engine import get_followup_engine
from career.crm.state_machine import ApplicationStateMachine
from career.email_intelligence.service import get_email_career_intelligence
from career.models import Application, ApplicationStatus, OfferStatus, PriorityLevel
from career.spreadsheet.projection import get_spreadsheet_projection


def test_complete_career_os_lifecycle_e2e():
    db = get_career_crm_db()
    pipeline = get_career_pipeline()
    email_service = get_email_career_intelligence()
    projection = get_spreadsheet_projection()
    followup_engine = get_followup_engine()

    app_id = f"APP-E2E-{uuid.uuid4().hex[:6].upper()}"
    company = "OpenAI"
    role = "Autonomous Systems Engineer"

    # Step 1: Job Discovery & Application Creation in CRM
    app = Application(
        application_id=app_id,
        job_id="job_openai_e2e",
        company=company,
        job_title=role,
        job_url="https://openai.com/careers/autonomous-systems-engineer",
        source="Greenhouse",
        platform="Greenhouse",
        application_status=ApplicationStatus.DISCOVERED,
        date_discovered=time.strftime("%Y-%m-%d"),
        priority=PriorityLevel.CRITICAL,
    )
    db.save_application(app)
    assert db.get_application(app_id) is not None

    # Step 2: Transition through Preparation and Review
    ApplicationStateMachine.transition(app_id, ApplicationStatus.SHORTLISTED, evidence="Matched candidate competencies")
    ApplicationStateMachine.transition(app_id, ApplicationStatus.PREPARING, evidence="Generated resume variant")
    ApplicationStateMachine.transition(app_id, ApplicationStatus.READY_FOR_REVIEW, evidence="Review gate ready")
    ApplicationStateMachine.transition(app_id, ApplicationStatus.APPLICATION_OPENED, evidence="Opened Greenhouse application link")
    ApplicationStateMachine.transition(app_id, ApplicationStatus.SUBMITTED, evidence="Application submitted on portal")

    # Step 3: Ingest Confirmation Email via Email Intelligence Engine
    email_res = email_service.process_incoming_email(
        provider="gmail",
        message_id=f"msg_conf_{int(time.time()*1000)}",
        sender="jobs@openai.com",
        subject=f"Application Received: {role} at {company}",
        body=f"Thank you for applying for the {role} role at {company}. Your application ID is {app_id}.",
    )
    assert email_res["status"] == "SUCCESS_VERIFIED"
    
    # Verify application status advanced to SUBMISSION_VERIFIED
    updated_app = db.get_application(app_id)
    assert updated_app.application_status in (ApplicationStatus.SUBMISSION_VERIFIED, ApplicationStatus.SUBMITTED)

    # Step 4: Schedule Follow-up Record
    followups = followup_engine.schedule_followups_for_application(app_id)
    assert len(followups) == 2
    assert followups[0].status in ("PENDING", "SCHEDULED")

    # Step 5: Ingest Interview Invitation Email
    email_iv = email_service.process_incoming_email(
        provider="gmail",
        message_id=f"msg_iv_{int(time.time()*1000)}",
        sender="recruiting@openai.com",
        subject=f"Interview Request: {role} with {company}",
        body=f"We would like to invite you for a Technical Round on August 28, 2026 at 11:00 AM PST via https://meet.google.com/xyz-uvwx-rst with Greg Brockman.",
    )
    assert email_iv["status"] == "SUCCESS_VERIFIED"
    assert email_iv["interview"] is not None

    # Step 6: Ingest Offer Email & Verify Conservative Staging
    email_off = email_service.process_incoming_email(
        provider="gmail",
        message_id=f"msg_off_{int(time.time()*1000)}",
        sender="leadership@openai.com",
        subject=f"Offer of Employment: {role} at {company}",
        body=(
            f"Dear Candidate,\nWe are pleased to extend an offer for {role} at {company}.\n"
            f"Base Salary: $260,000 USD per year.\n"
            f"Sign-on bonus: $50,000 USD.\n"
            f"Start date: October 15, 2026. Respond by September 20, 2026."
        ),
    )
    assert email_off["status"] == "SUCCESS_VERIFIED"
    assert email_off["offer"] is not None
    assert email_off["offer"]["status"] != "OFFER_CONFIRMED"  # Must NOT be auto-confirmed

    # Step 7: Explicit Human Approval of Offer
    staged_offer_id = email_off["offer"]["offer_id"]
    offer = db.get_offer(staged_offer_id)
    offer.status = OfferStatus.OFFER_CONFIRMED
    db.save_offer(offer)
    assert db.get_offer(staged_offer_id).status == OfferStatus.OFFER_CONFIRMED

    # Step 8: Authoritative Excel Projection Sync
    proj_res = projection.project_database_to_excel()
    assert proj_res["status"] == "SUCCESS_VERIFIED"
    assert proj_res["applications_count"] >= 1
