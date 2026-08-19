"""Integration tests for WebSocket Connection Ticket & Event Broadcasting."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from brjarvis.web.api.routes.auth import issue_ws_ticket, verify_and_consume_ws_ticket
from brjarvis.web.api.server import create_app
from brjarvis.web.api.state import SERVER_API_KEY


@pytest.mark.integration
def test_websocket_ticket_lifecycle():
    """Verify single-use WebSocket ticket creation and verification."""
    ticket = issue_ws_ticket()
    assert ticket is not None
    assert len(ticket) >= 16

    assert verify_and_consume_ws_ticket(ticket) is True
    # Single-use consumption ensures second check fails
    assert verify_and_consume_ws_ticket(ticket) is False


@pytest.mark.integration
def test_websocket_requires_authentication_and_consumes_ticket():
    client = TestClient(create_app())

    with pytest.raises(WebSocketDisconnect) as unauthenticated:
        with client.websocket_connect("/ws"):
            pass
    assert unauthenticated.value.code == 4001

    login = client.post("/api/auth/login", json={"api_key": SERVER_API_KEY})
    assert login.status_code == 200
    ticket_response = client.post("/api/auth/ws-ticket")
    assert ticket_response.status_code == 200
    ticket = ticket_response.json()["ticket"]

    with client.websocket_connect(f"/ws?ticket={ticket}") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "ServerReady"

    unauthenticated_client = TestClient(create_app())
    with pytest.raises(WebSocketDisconnect) as reused:
        with unauthenticated_client.websocket_connect(f"/ws?ticket={ticket}"):
            pass
    assert reused.value.code == 4001
