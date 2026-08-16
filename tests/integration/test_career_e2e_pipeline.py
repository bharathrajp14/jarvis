# tests/integration/test_career_e2e_pipeline.py — Full End-to-End Career OS Pipeline Integration Tests
import pytest
from pathlib import Path
from career.profile_manager import CareerProfileManager
from career.job_engine.finder import JobFinder
from career.resume_engine.tailoring import ResumeTailoringEngine
from career.resume_engine.exporter import ResumeExportPipeline
from career.ats_engine.scorer import ATSEngine
from career.application_engine.package_builder import ApplicationPackageBuilder
from career.application_engine.assistant import ManualApplicationAssistant
from career.application_engine.tracker import ApplicationTracker
from career.models import ApplicationStatus
from fastapi.testclient import TestClient
from api.server import create_app
from api.state import SERVER_API_KEY


@pytest.fixture
def app_client():
    app = create_app()
    headers = {"X-API-Key": SERVER_API_KEY} if SERVER_API_KEY else {}
    return TestClient(app, headers=headers)


def test_career_e2e_lifecycle(tmp_path):
    """
    Complete lifecycle integration test:
    Profile -> Search -> Match -> Tailor -> Score -> Package -> Track -> REST API.
    """
    # 1. Profile Manager
    pm = CareerProfileManager(storage_dir=tmp_path / "profile")
    profile = pm.get_profile()
    assert profile.contact.full_name == "Bharath Raj"

    # 2. Search & Match
    finder = JobFinder.get_instance()
    results = finder.search_and_match(query_or_filters="Autonomous AI Systems Architect", limit=3)
    assert len(results) > 0
    top_result = results[0]
    job = top_result.job
    assert top_result.match.overall_score > 70.0

    # 3. Tailor Resume & Score ATS
    tailored_schema, diff = ResumeTailoringEngine.tailor_resume(
        profile=profile,
        job_description=job.description,
        target_role=job.title,
        company_name=job.company,
    )
    ats_score = ATSEngine.evaluate_resume(tailored_schema, job_description=job.description)
    assert ats_score.overall_score >= 80.0

    # 4. Build Package & Verify Physical Artifacts
    builder = ApplicationPackageBuilder(base_dir=tmp_path / "apps")
    pkg = builder.build_package(profile=profile, job=job)
    assert Path(pkg.resume_pdf_path).exists()
    assert Path(pkg.cover_letter_pdf_path).exists()
    assert Path(pkg.job_description_html_path).exists()

    # 5. Track & Lifecycle Transitions
    tracker = ApplicationTracker(storage_dir=tmp_path / "track")
    app_rec = tracker.create_application(job=job, status=ApplicationStatus.READY_FOR_REVIEW, package_id=pkg.package_id)
    assert app_rec.status == ApplicationStatus.READY_FOR_REVIEW

    # Advance to SUBMISSION_VERIFIED
    updated = tracker.update_status(
        application_id=app_rec.application_id,
        new_status=ApplicationStatus.SUBMISSION_VERIFIED,
        note="Verified submission receipt APP-928104",
        confirmation_id="APP-928104"
    )
    assert updated.status == ApplicationStatus.SUBMISSION_VERIFIED
    assert updated.confirmation_id == "APP-928104"


def test_career_rest_api_endpoints(app_client):
    """Test all Career OS REST API endpoints."""
    # 1. Profile
    r_prof = app_client.get("/api/career/profile")
    assert r_prof.status_code == 200
    assert r_prof.json()["profile"]["contact"]["full_name"] == "Bharath Raj"

    # 2. Templates
    r_tmpl = app_client.get("/api/career/resumes/templates")
    assert r_tmpl.status_code == 200
    assert len(r_tmpl.json()["templates"]) == 10

    # 3. Job Search
    r_jobs = app_client.get("/api/career/jobs/search?query=AI+Engineer&limit=2")
    assert r_jobs.status_code == 200
    assert "matches" in r_jobs.json()

    # 4. ATS Scoring
    r_ats = app_client.post("/api/career/ats/score", json={"target_role": "Autonomous Systems Engineer"})
    assert r_ats.status_code == 200
    assert r_ats.json()["overall_score"] > 50.0

    # 5. Analytics
    r_ana = app_client.get("/api/career/analytics")
    assert r_ana.status_code == 200
    assert "response_rate" in r_ana.json()
