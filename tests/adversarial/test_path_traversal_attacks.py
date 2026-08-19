"""Adversarial Security Tests: Path Traversal & Sandbox Escape Attempts."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient

from brjarvis.career.api_routes import download_career_file
from brjarvis.security.path_policy import PathTier, get_path_policy
from brjarvis.web.api.server import create_app
from brjarvis.web.api.state import SERVER_API_KEY


@pytest.mark.adversarial
def test_path_traversal_relative_parent_escape():
    """Verify dot-dot traversal escaping workspace is flagged as critical secret / unsafe."""
    policy = get_path_policy()
    evil_paths = [
        "../../../../Windows/System32/config/SAM",
        "workspace/../../../../etc/shadow",
        "..\\..\\..\\Windows\\win.ini",
        "workspace/..\\..\\secrets.json",
        ".env",
        ".env.local"
    ]
    for p in evil_paths:
        assert policy.is_safe_resource(p) is False or policy.get_tier(p) == PathTier.TIER_2_CRITICAL_SECRETS


@pytest.mark.adversarial
def test_career_download_rejects_existing_file_outside_workspace(tmp_path):
    """An existing readable file must not bypass workspace containment."""
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("sensitive", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        download_career_file(str(outside))

    assert exc_info.value.status_code == 403


@pytest.mark.adversarial
def test_static_route_rejects_encoded_parent_traversal():
    """Encoded parent segments must never escape the configured web root."""
    client = TestClient(create_app(), headers={"X-API-Key": SERVER_API_KEY})
    response = client.get("/%2e%2e%2fpyproject.toml")

    assert response.status_code == 404
    assert "build-system" not in response.text
