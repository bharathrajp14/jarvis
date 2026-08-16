# tests/unit/test_career_profile.py — Unit Tests for Canonical Profile Manager
import pytest
from pathlib import Path
from career.models import CareerProfile, FactSource, ProfileFact
from career.profile_manager import CareerProfileManager


@pytest.fixture
def temp_profile_mgr(tmp_path):
    return CareerProfileManager(storage_dir=tmp_path)


def test_profile_initialization_and_retrieval(temp_profile_mgr):
    profile = temp_profile_mgr.get_profile()
    assert profile is not None
    assert profile.contact.full_name == "Bharath Raj"
    assert len(profile.experience) >= 1
    assert len(profile.skills) >= 1


def test_profile_validation_completeness(temp_profile_mgr):
    profile = temp_profile_mgr.get_profile()
    val = temp_profile_mgr.validate_profile(profile)
    assert val["score"] >= 80
    assert val["status"] in ("GOOD", "EXCELLENT")
    assert isinstance(val["missing_fields"], list)
    assert isinstance(val["conflicts"], list)


def test_onboarding_questions_and_answers(temp_profile_mgr):
    profile = temp_profile_mgr.get_profile()
    # Temporarily clear target roles
    profile.preferences.target_roles = []
    qs = temp_profile_mgr.get_onboarding_questions(profile)
    assert any(q["field"] == "preferences.target_roles" for q in qs)

    # Apply answer
    updated = temp_profile_mgr.apply_onboarding_answers(
        {"preferences.target_roles": ["Autonomous Systems Architect", "AI Engineer"]},
        profile=profile
    )
    assert "Autonomous Systems Architect" in updated.preferences.target_roles
    assert "preferences.target_roles" in updated.provenance
    assert updated.provenance["preferences.target_roles"].source == FactSource.USER_INPUT


def test_conflict_detection_on_dates(temp_profile_mgr):
    profile = temp_profile_mgr.get_profile()
    if profile.experience:
        profile.experience[0].start_date = "2024-05"
        profile.experience[0].end_date = "2023-01"  # Start after end
        val = temp_profile_mgr.validate_profile(profile)
        assert len(val["conflicts"]) > 0
        assert "dates" in val["conflicts"][0]["field"]
