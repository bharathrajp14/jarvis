"""Unit tests for Career Profile Manager."""
from __future__ import annotations

import pytest
from brjarvis.career.profile_manager import CareerProfileManager
from brjarvis.career.models import CareerProfile, ContactInfo


@pytest.mark.unit
def test_career_profile_load_and_update(tmp_path):
    """Verify career profile manager loads and writes profile correctly."""
    mgr = CareerProfileManager(storage_dir=tmp_path)
    
    profile = CareerProfile(
        profile_id="master_profile",
        summary="Senior AI Systems Engineer",
        contact=ContactInfo(full_name="Bharath Raj", email="bharath@example.com", phone="+1-555-0199"),
    )
    mgr.save_profile(profile)
    loaded = mgr.get_profile("master_profile")
    
    assert loaded is not None
    assert loaded.contact.full_name == "Bharath Raj"
    assert loaded.summary == "Senior AI Systems Engineer"
