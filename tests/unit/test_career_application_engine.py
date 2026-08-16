# tests/unit/test_career_application_engine.py — Unit Tests for Application Engine, Package Builder & Tracker
import pytest
from pathlib import Path
from career.application_engine import (
    ApplicationPackageBuilder,
    ApplicationTracker,
    ApplicationSubmissionVerifier,
    DuplicateApplicationGuard,
    ManualApplicationAssistant,
    PlatformPolicyEngine,
    QuestionEngine,
)
from career.models import (
    ApplicationQuestion,
    ApplicationRecord,
    ApplicationStatus,
    JobPosting,
    PlatformPolicyState,
)
from career.profile_manager import get_profile_manager


def test_platform_policy_engine():
    p_gh = PlatformPolicyEngine.evaluate_policy("Greenhouse")
    assert p_gh.policy_state == PlatformPolicyState.REVIEW_REQUIRED

    p_li = PlatformPolicyEngine.evaluate_policy("LinkedIn")
    assert p_li.policy_state == PlatformPolicyState.MANUAL_REQUIRED
    assert p_li.captcha_expected is True

    p_unk = PlatformPolicyEngine.evaluate_policy("RandomJobBoard99")
    assert p_unk.policy_state == PlatformPolicyState.MANUAL_REQUIRED


def test_sensitive_question_guard():
    profile = get_profile_manager().get_profile()
    questions = [
        ApplicationQuestion(question_id="q1", question_text="Full Name"),
        ApplicationQuestion(question_id="q2", question_text="Do you require visa sponsorship now or in the future?"),
        ApplicationQuestion(question_id="q3", question_text="What are your desired salary expectations?"),
    ]
    mapped = QuestionEngine.map_questions(profile, questions)
    
    assert mapped[0].requires_confirmation is False
    assert mapped[1].requires_confirmation is True
    assert mapped[1].sensitive_category == "sponsorship"
    assert mapped[2].requires_confirmation is True
    assert mapped[2].sensitive_category == "salary"


def test_application_package_builder(tmp_path):
    profile = get_profile_manager().get_profile()
    job = JobPosting(
        job_id="test_anthropic_pkg_01",
        source="test",
        platform="Greenhouse",
        company="Anthropic",
        title="AI Engineer",
        location="Remote",
        description="Autonomous AI runtime engineer with Python mastery.",
    )

    builder = ApplicationPackageBuilder(base_dir=tmp_path)
    pkg = builder.build_package(profile, job)

    assert pkg.package_id.startswith("pkg_")
    assert Path(pkg.resume_docx_path).exists()
    assert Path(pkg.resume_pdf_path).exists()
    assert Path(pkg.resume_html_path).exists()
    assert Path(pkg.cover_letter_pdf_path).exists()
    assert Path(pkg.job_description_html_path).exists()
    assert Path(pkg.answers_json_path).exists()


def test_duplicate_application_guard():
    job = JobPosting(job_id="job_scale_829", source="s", platform="Greenhouse", company="Scale AI", title="Senior AI Architect", location="Remote")
    
    existing = [
        ApplicationRecord(
            application_id="app_123",
            job_id="job_scale_829",
            company="Scale AI",
            role_title="Senior AI Architect",
            status=ApplicationStatus.SUBMITTED,
        )
    ]

    is_dup, reason, prior = DuplicateApplicationGuard.check_duplicate(job, existing)
    assert is_dup is True
    assert prior is not None
    assert prior.application_id == "app_123"


def test_submission_verification_evidence():
    # 1. Negative case (no evidence)
    v1 = ApplicationSubmissionVerifier.verify_submission({})
    assert v1.verified is False

    # 2. Positive case (confirmation ID)
    v2 = ApplicationSubmissionVerifier.verify_submission({
        "confirmation_id": "CONF-928104",
        "confirmation_url": "https://boards.greenhouse.io/anthropic/jobs/4928190/confirmation"
    })
    assert v2.verified is True
    assert "CONF-928104" in v2.evidence
