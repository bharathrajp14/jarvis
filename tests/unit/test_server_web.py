# tests/test_server_web.py — Unit & Integration tests for Web Server Endpoints
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_api_connector_config(client):
    response = client.post("/api/connector/config", json={"connector": "GitHub Developer", "api_key": "ghp_test123456789"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "GitHub Developer" in data.get("message", "")
    data = response.json()
    assert data.get("status") in ("ok", "online")


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

    res_root = client.get("/")
    assert res_root.status_code in (200, 304)

    res_web = client.get("/web")
    assert res_web.status_code in (200, 304)

    res_galaxy = client.get("/web/galaxy.html")
    assert res_galaxy.status_code in (200, 304)

    res_galaxy_alias = client.get("/galaxy")
    assert res_galaxy_alias.status_code in (200, 304)


def test_root_static_file_routing(client):
    res_css = client.get("/style.css")
    assert res_css.status_code in (200, 304)

    res_js = client.get("/app.js")
    assert res_js.status_code in (200, 304)


def test_html_404_fallback(client):
    res_404_json = client.get("/api/unknown_endpoint")
    assert res_404_json.status_code == 404
    assert res_404_json.headers.get("content-type", "").startswith("application/json")

    res_404_html = client.get("/invalid_page_path", headers={"Accept": "text/html"})
    assert res_404_html.status_code in (200, 404)


def test_port_conflict_fallback(monkeypatch):
    from ui_mark import _find_available_jarvis_port, _server_port
    monkeypatch.setattr("ui_mark._port_free", lambda port: port != 8000)
    monkeypatch.setattr("ui_mark._is_jarvis_running", lambda port: False)
    fallback_port = _find_available_jarvis_port(8000)
    assert fallback_port != 8000
    assert fallback_port in (8080, 8088, 8888, 5000, 8001, 8002)


