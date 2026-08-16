# career/application_engine/assistant.py — Interactive Manual Application Assistant
from __future__ import annotations

import logging
import time
import webbrowser
from typing import Any, Dict, List, Optional

from career.application_engine.duplicate_guard import DuplicateApplicationGuard
from career.application_engine.package_builder import ApplicationPackageBuilder
from career.application_engine.policy import PlatformPolicyEngine
from career.application_engine.questions import QuestionEngine
from career.application_engine.tracker import ApplicationTracker
from career.application_engine.verifier import ApplicationSubmissionVerifier
from career.models import (
    ApplicationPackage,
    ApplicationQuestion,
    ApplicationRecord,
    ApplicationStatus,
    CareerProfile,
    JobPosting,
    PlatformPolicyState,
)
from career.profile_manager import get_profile_manager
from core.execution.verifier import get_universal_verifier

logger = logging.getLogger("JARVIS.ApplicationAssistant")


class ManualApplicationAssistant:
    """
    Core Product Assistant for Job Applications.
    
    Standard Flow:
    1. READ       - Inspect JobPosting & requirements
    2. GUARD      - Check for prior duplicate applications
    3. TAILOR     - Build tailored resume & cover letter package
    4. MAP        - Map candidate facts to form questions (flagging sensitive items)
    5. POLICY     - Evaluate platform automation policy (API / Browser / Manual)
    6. LAUNCH     - Open application portal in browser
    7. HANDOFF    - Present pre-filled answers and wait for user submission
    8. TRACK      - Record application lifecycle in persistent tracker
    """

    def __init__(self):
        self.tracker = ApplicationTracker.get_instance()
        self.package_builder = ApplicationPackageBuilder()
        self.profile_mgr = get_profile_manager()
        self.verifier = get_universal_verifier()

    def prepare_and_assist(
        self,
        job: JobPosting,
        profile: Optional[CareerProfile] = None,
        auto_open_browser: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute full assisted application flow for a selected job posting.
        """
        p = profile or self.profile_mgr.get_profile()

        # 1. Duplicate Application Check
        existing_apps = self.tracker.list_applications(limit=500)
        is_dup, dup_reason, prior_app = DuplicateApplicationGuard.check_duplicate(job, existing_apps)
        if is_dup:
            return {
                "success": False,
                "status": "DUPLICATE_PREVENTED",
                "message": dup_reason,
                "prior_application_id": prior_app.application_id if prior_app else None,
            }

        # 2. Evaluate Platform Policy
        policy = PlatformPolicyEngine.evaluate_policy(job.platform, job=job)

        # 3. Form Application Questions & Semantic Answers
        # Standard generic form fields
        raw_questions = [
            ApplicationQuestion(question_id="full_name", question_text="Full Name", required=True),
            ApplicationQuestion(question_id="email", question_text="Email Address", required=True),
            ApplicationQuestion(question_id="phone", question_text="Phone Number", required=True),
            ApplicationQuestion(question_id="location", question_text="Location / City", required=True),
            ApplicationQuestion(question_id="linkedin", question_text="LinkedIn URL", required=False),
            ApplicationQuestion(question_id="github", question_text="GitHub URL", required=False),
            ApplicationQuestion(question_id="work_auth", question_text="Are you legally authorized to work in this location?", required=True),
            ApplicationQuestion(question_id="sponsorship", question_text="Will you require visa sponsorship now or in the future?", required=True),
            ApplicationQuestion(question_id="salary", question_text="Desired Salary Expectations", required=False),
            ApplicationQuestion(question_id="notice", question_text="Notice Period / Availability", required=False),
        ]
        mapped_questions = QuestionEngine.map_questions(p, raw_questions)
        answers_dict = {q.question_id: q.suggested_answer for q in mapped_questions if q.suggested_answer}

        # 4. Build Complete Verified Application Package
        package = self.package_builder.build_package(
            profile=p,
            job=job,
            answers=answers_dict,
        )

        # 5. Create / Update Tracking Record
        app_record = self.tracker.create_application(
            job=job,
            status=ApplicationStatus.READY_FOR_REVIEW,
            package_id=package.package_id,
            notes=[
                f"Application prepared for {job.company}.",
                f"Platform Policy: {policy.policy_state.value}.",
                f"Package ID: {package.package_id}.",
            ],
        )

        # 6. Open Application URL if requested
        browser_opened = False
        if auto_open_browser and job.application_url:
            try:
                # Use standard system browser launcher
                webbrowser.open(job.application_url)
                browser_opened = True
                logger.info(f"🌐 Application URL opened in browser: {job.application_url}")
            except Exception as e:
                logger.warning(f"Could not open browser URL: {e}")

        sensitive_questions = [
            q.to_dict() for q in mapped_questions if q.requires_confirmation
        ]

        return {
            "success": True,
            "status": "READY_FOR_REVIEW",
            "application_id": app_record.application_id,
            "package_id": package.package_id,
            "company": job.company,
            "role": job.title,
            "application_url": job.application_url,
            "browser_opened": browser_opened,
            "policy": policy.to_dict(),
            "resume_pdf": package.resume_pdf_path,
            "resume_docx": package.resume_docx_path,
            "cover_letter_pdf": package.cover_letter_pdf_path,
            "suggested_answers": answers_dict,
            "sensitive_questions_requiring_confirmation": sensitive_questions,
            "instructions": (
                "The application page has been opened and your tailored materials are ready. "
                "Review the answers and submit when ready. Control is currently with you."
            ),
        }

    def record_submission(
        self,
        application_id: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Record verified application submission outcome."""
        v_outcome = ApplicationSubmissionVerifier.verify_submission(evidence)

        new_status = ApplicationStatus.SUBMISSION_VERIFIED if v_outcome.verified else ApplicationStatus.SUBMITTED
        note = f"Submission recorded. Evidence: {v_outcome.details}"

        rec = self.tracker.update_status(
            application_id=application_id,
            new_status=new_status,
            note=note,
            confirmation_id=evidence.get("confirmation_id"),
            confirmation_url=evidence.get("confirmation_url"),
        )

        return {
            "success": True,
            "application_id": application_id,
            "status": new_status.value,
            "verified": v_outcome.verified,
            "evidence": v_outcome.evidence or v_outcome.details,
        }
