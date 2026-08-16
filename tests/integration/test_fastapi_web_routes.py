"""Integration tests for FastAPI REST Endpoints via TestClient."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from apps.web.api.server import create_app


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
    
    resp = client.get("/api/connectors")
    assert resp.status_code == 200
    assert isinstance(resp.json(), (list, dict))
