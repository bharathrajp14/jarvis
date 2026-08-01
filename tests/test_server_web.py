# tests/test_server_web.py — Unit & Integration tests for Web Server Endpoints
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ("ok", "online")


def test_api_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "online"
    assert "cpu" in data
    assert "ram" in data
    assert "disk" in data


def test_api_skills_endpoint(client):
    response = client.get("/api/skills")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_api_connectors_endpoint(client):
    response = client.get("/api/connectors")
    assert response.status_code == 200
    data = response.json()
    assert "connectors" in data
    assert len(data["connectors"]) > 0


def test_api_backend_switch(client):
    response = client.post("/api/backend/switch", json={"backend": "gemini"})
    assert response.status_code in (200, 400)


def test_static_web_pages(client):
    res_index = client.get("/web/index.html")
    assert res_index.status_code in (200, 304)

    res_galaxy = client.get("/web/galaxy.html")
    assert res_galaxy.status_code in (200, 304)
