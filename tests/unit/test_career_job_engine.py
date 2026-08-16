# tests/unit/test_career_job_engine.py — Unit Tests for Job Engine, Adapters, Deduplication & Matcher
import pytest
from career.job_engine import (
    JobFinder,
    JobMatcher,
    JobRanker,
    JobDeduplicator,
    SearchFilters,
    GreenhouseAdapter,
    LeverAdapter,
    AshbyAdapter,
)
from career.models import JobPosting
from career.profile_manager import get_profile_manager


def test_job_deduplicator():
    j1 = JobPosting(job_id="j1", source="s1", platform="Greenhouse", company="Stripe", title="Systems Engineer", location="Remote", application_url="https://jobs.stripe.com/1?utm_source=feed")
    j2 = JobPosting(job_id="j2", source="s2", platform="Lever", company="Stripe", title="Systems Engineer", location="Remote", application_url="https://jobs.stripe.com/1?ref=aggregator")
    j3 = JobPosting(job_id="j3", source="s3", platform="Ashby", company="Linear", title="Frontend Engineer", location="Remote", application_url="https://jobs.linear.app/3")
    
    deduped = JobDeduplicator.deduplicate([j1, j2, j3])
    assert len(deduped) == 2  # j1 and j2 are identical company/title/location and url


def test_greenhouse_and_lever_adapters():
    gh = GreenhouseAdapter()
    filters = SearchFilters(limit=5)
    gh_jobs = gh.discover_jobs(filters)
    assert len(gh_jobs) > 0
    assert gh_jobs[0].platform == "Greenhouse"

    lev = LeverAdapter()
    lev_jobs = lev.discover_jobs(filters)
    assert len(lev_jobs) > 0
    assert lev_jobs[0].platform == "Lever"


def test_10_factor_job_matcher():
    profile = get_profile_manager().get_profile()
    job = JobPosting(
        job_id="test_anthropic_eng",
        source="test",
        platform="Greenhouse",
        company="Anthropic",
        title="Autonomous AI Systems Architect",
        location="Remote",
        remote_type="remote",
        technologies=["Python", "FastAPI", "Playwright", "Docker", "ChromaDB"],
        requirements=["Deep expertise in agentic loops, Python, and async runtimes."],
    )
    
    match = JobMatcher.match(profile, job)
    assert match.overall_score >= 85.0
    assert match.skills_score >= 80.0
    assert match.location_score == 100.0
    assert len(match.matched_skills) > 0
    assert len(match.key_strengths) > 0


def test_natural_language_job_query_parsing():
    finder = JobFinder.get_instance()
    f1 = finder.parse_natural_language_query("Find remote backend python developer jobs in Madurai")
    assert f1.remote_only is True
    assert f1.location == "Madurai"
    assert any("backend" in r.lower() or "python" in r.lower() for r in f1.target_roles)
