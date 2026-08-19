"""Integration tests for FastAPI REST Endpoints via TestClient."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from brjarvis.web.api.server import create_app
from brjarvis.web.api.state import SERVER_API_KEY, WEB_DIR


@pytest.mark.integration
def test_fastapi_health_endpoint():
    """Verify GET /health returns 200 OK."""
    app = create_app()
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data or "ok" in str(data).lower()


@pytest.mark.integration
def test_fastapi_connectors_endpoint():
    """Verify GET /api/connectors returns available integrations."""
    app = create_app()
    client = TestClient(app)

    unauthorized = client.get("/api/connectors")
    assert unauthorized.status_code == 401

    resp = client.get("/api/connectors", headers={"X-API-Key": SERVER_API_KEY})
    assert resp.status_code == 200
    assert isinstance(resp.json(), (list, dict))


@pytest.mark.integration
def test_fastapi_login_creates_authenticated_cookie_session():
    """The API key is exchanged for an HttpOnly session instead of bypassing auth locally."""
    client = TestClient(create_app())

    invalid = client.post("/api/auth/login", json={"api_key": "invalid-key"})
    assert invalid.status_code == 401

    valid = client.post("/api/auth/login", json={"api_key": SERVER_API_KEY})
    assert valid.status_code == 200

    assert "jarvis_session" in valid.cookies
    assert "session_token" not in valid.json()

    authenticated = client.get("/api/connectors")

    assert authenticated.status_code == 200


@pytest.mark.integration
def test_dashboard_career_routes_match_openapi_contract():
    app = create_app()
    paths = app.openapi()["paths"]

    assert "get" in paths["/api/career/jobs/search"]
    assert "post" in paths["/api/career/resumes/create"]
    assert "post" in paths["/api/career/ats/score"]
    assert "post" in paths["/api/career/spreadsheet/sync"]

    dashboard_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "/api/career/jobs/search?query=" in dashboard_js
    assert "/api/career/resumes/create" in dashboard_js
    assert "/api/career/ats/score" in dashboard_js
    assert "/api/career/resume/generate" not in dashboard_js
    assert "/api/career/resume/ats-audit" not in dashboard_js
