"""Integration tests for WebSocket Connection Ticket & Event Broadcasting."""
from __future__ import annotations

import pytest
from apps.web.api.routes.auth import issue_ws_ticket, verify_and_consume_ws_ticket


@pytest.mark.integration
def test_websocket_ticket_lifecycle():
    """Verify single-use WebSocket ticket creation and verification."""
    ticket = issue_ws_ticket()
    assert ticket is not None
    assert len(ticket) >= 16

    assert verify_and_consume_ws_ticket(ticket) is True
    # Single-use consumption ensures second check fails
    assert verify_and_consume_ws_ticket(ticket) is False
