# tests/unit/test_career_ats_engine.py — Unit Tests for 7-Factor ATS Engine
import pytest
from career.ats_engine import ATSEngine, ATSScoreReport
from career.profile_manager import get_profile_manager
from career.resume_engine.renderer import ResumeRenderer


def test_ats_baseline_scoring():
    profile = get_profile_manager().get_profile()
    schema = ResumeRenderer.schema_from_profile(profile)
    
    rep = ATSEngine.evaluate_resume(schema)
    assert isinstance(rep, ATSScoreReport)
    assert 0.0 <= rep.overall_score <= 100.0
    assert rep.grade in ("A+", "A", "B", "C", "D")
    assert rep.section_recognition_score >= 80.0
    assert rep.parsing_risk_score >= 80.0


def test_ats_scoring_against_job_description():
    profile = get_profile_manager().get_profile()
    schema = ResumeRenderer.schema_from_profile(profile)
    
    jd = "Looking for Senior AI Engineer skilled in Python, FastAPI, Docker, Playwright, PyTorch, ChromaDB, and high-scale systems."
    rep = ATSEngine.evaluate_resume(schema, job_description=jd)
    
    assert rep.keyword_coverage_score > 60.0
    assert len(rep.matched_keywords) > 0
    assert isinstance(rep.recommended_changes, list)


def test_ats_parsing_risk_on_missing_contact():
    profile = get_profile_manager().get_profile()
    schema = ResumeRenderer.schema_from_profile(profile)
    schema.contact_email = ""  # Strip email to test deduction
    
    rep = ATSEngine.evaluate_resume(schema)
    assert rep.parsing_risk_score < 80.0
    assert any("email" in risk.lower() for risk in rep.critical_risks)
