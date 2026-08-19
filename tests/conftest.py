"""
tests/conftest.py — Global Pytest Configuration and Fixtures for BR JARVIS MK40.2+
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Security-sensitive modules read these values at import time. Tests use a
# deterministic non-production key and still exercise the real auth boundary.
os.environ.setdefault("JARVIS_TEST_MODE", "true")
os.environ.setdefault("JARVIS_SERVER_API_KEY", "brjarvis-test-api-key-32-characters")
os.environ.setdefault("JARVIS_PERMISSION_MODE", "confirm_destructive")

# Ensure project root & src are on sys.path
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
for _p in [str(_SRC), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Ensure safe testing environment flags are active."""
    os.environ["JARVIS_TEST_MODE"] = "true"
    os.environ["JARVIS_PERMISSION_MODE"] = "confirm_destructive"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    yield
    os.environ.pop("JARVIS_TEST_MODE", None)


@pytest.fixture
def temp_workspace(tmp_path):
    """Provide a dedicated temporary workspace directory for test execution."""
    ws = tmp_path / "test_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "documents").mkdir(parents=True, exist_ok=True)
    (ws / "resumes").mkdir(parents=True, exist_ok=True)
    (ws / "career").mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def temp_runtime(tmp_path):
    """Provide a dedicated temporary runtime directory for test logs and state."""
    rt = tmp_path / "test_runtime"
    rt.mkdir(parents=True, exist_ok=True)
    (rt / "logs").mkdir(parents=True, exist_ok=True)
    (rt / "captures").mkdir(parents=True, exist_ok=True)
    (rt / "reports").mkdir(parents=True, exist_ok=True)
    (rt / "state").mkdir(parents=True, exist_ok=True)
    (rt / "state" / "memory_db").mkdir(parents=True, exist_ok=True)
    return rt


@pytest.fixture
def sample_profile_data():
    """Return standard test profile data for Career OS tests."""
    return {
        "name": "Bharath Raj",
        "title": "Lead AI Systems & Autonomous Agent Engineer",
        "email": "bharath@example.com",
        "phone": "+1-555-0199",
        "location": "San Francisco, CA (Remote)",
        "summary": "AI Systems Engineer specializing in autonomous agent architectures, FastAPI backends, and multi-model LLM orchestration.",
        "skills": [
            "Python",
            "FastAPI",
            "PyTorch",
            "Autonomous Agents",
            "System Architecture",
            "SQLite WAL",
            "Three.js",
            "Docker",
            "REST APIs",
            "WebSockets",
        ],
        "experience": [
            {
                "company": "Anthropic AI Lab",
                "role": "Senior AI Systems Architect",
                "period": "2023 - Present",
                "highlights": [
                    "Designed high-throughput LLM gateway routing with Shannon entropy analysis, reducing latency by 45%.",
                    "Architected SQLite WAL thread-safe persistence and vector indexing for 500,000+ items.",
                ],
            }
        ],
        "education": [
            {
                "institution": "Stanford University",
                "degree": "B.S. in Computer Science (Artificial Intelligence)",
                "year": "2022",
            }
        ],
    }


@pytest.fixture
def sample_job_description():
    """Return standard job description for ATS scoring tests."""
    return """
    Senior AI Backend Engineer
    Company: Scale AI Systems
    Location: Remote

    Requirements:
    - 4+ years experience with Python and FastAPI backend development.
    - Deep expertise in Autonomous Agent architectures and LLM prompt optimization.
    - Proven track record with SQLite WAL optimization, concurrency locks, and WebSocket streaming.
    - Strong communication skills and ability to design clean REST APIs.
    - Bachelor's degree in Computer Science or equivalent experience.
    """
