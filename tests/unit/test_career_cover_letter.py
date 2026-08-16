# tests/unit/test_career_cover_letter.py — Unit Tests for Cover Letter Generator
import pytest
from pathlib import Path
from career.cover_letter import CoverLetterGenerator
from career.models import JobPosting
from career.profile_manager import get_profile_manager


def test_cover_letter_generation():
    profile = get_profile_manager().get_profile()
    job = JobPosting(
        job_id="test_anthropic_01",
        source="test",
        platform="Greenhouse",
        company="Anthropic",
        title="Systems & Autonomous AI Engineer",
        location="Remote",
    )
    
    letter = CoverLetterGenerator.generate(profile, job)
    assert profile.contact.full_name in letter
    assert "Anthropic" in letter
    assert "Systems & Autonomous AI Engineer" in letter
    assert len(letter) > 300


def test_cover_letter_pdf_export(tmp_path):
    profile = get_profile_manager().get_profile()
    job = JobPosting(
        job_id="test_scale_02",
        source="test",
        platform="Greenhouse",
        company="Scale AI",
        title="Senior AI Architect",
        location="Remote",
    )
    letter = CoverLetterGenerator.generate(profile, job)
    pdf_path = tmp_path / "cover_letter_test.pdf"
    
    ok = CoverLetterGenerator.export_pdf(letter, pdf_path)
    assert ok is True
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500
