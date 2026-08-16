# tests/unit/test_career_canva_and_analytics.py — Unit Tests for Canva Adapter & Career Analytics
import pytest
from career.analytics import CareerAnalyticsEngine
from career.canva import CanvaAdapter, CanvaCapabilityProbe
from career.interview_prep import InterviewPrepGenerator
from career.models import JobPosting
from career.profile_manager import get_profile_manager
from career.resume_engine.renderer import ResumeRenderer


def test_canva_capability_probe():
    cap = CanvaCapabilityProbe.detect_capabilities()
    assert isinstance(cap.canva_connected, bool)
    assert cap.status_summary != ""


def test_canva_adapter_native_fallback():
    profile = get_profile_manager().get_profile()
    schema = ResumeRenderer.schema_from_profile(profile)
    
    adapter = CanvaAdapter()
    res = adapter.generate_resume(schema)
    assert res["status"] == "SUCCESS_VERIFIED"
    assert res["provider"] in ("native", "canva", "native_fallback")
    assert res["artifacts"]["all_verified"] is True


def test_career_analytics_engine():
    analytics = CareerAnalyticsEngine.compute_analytics()
    assert analytics.total_jobs_discovered >= 0
    assert 0.0 <= analytics.response_rate <= 100.0
    assert isinstance(analytics.status_counts, dict)


def test_interview_prep_generator():
    profile = get_profile_manager().get_profile()
    job = JobPosting(
        job_id="test_prep_01",
        source="test",
        platform="Greenhouse",
        company="Anthropic",
        title="Autonomous AI Systems Architect",
        location="Remote",
    )
    kit = InterviewPrepGenerator.generate_prep_kit(profile, job)
    assert kit.company_name == "Anthropic"
    assert len(kit.technical_questions) >= 3
    assert len(kit.star_stories) >= 1
    assert len(kit.questions_for_interviewer) >= 3
