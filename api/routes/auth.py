# api/routes/auth.py — Authentication & Short-Lived WebSocket Ticket Exchange
"""
Provides secure session authentication and one-time short-lived ticket issuance for WebSocket handshakes.
Prevents passing long-lived credentials in URL query parameters.
"""
from __future__ import annotations

import hmac
import logging
import secrets
import time
from typing import Dict, Optional
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from api.state import SERVER_API_KEY

logger = logging.getLogger("JARVIS.API.Auth")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Ticket storage: ticket_id -> expiry_timestamp
_TICKET_STORE: Dict[str, float] = {}
_TICKET_TTL_SECONDS = 60.0


def _prune_tickets() -> None:
    now = time.time()
    expired = [t for t, exp in _TICKET_STORE.items() if exp < now]
    for t in expired:
        _TICKET_STORE.pop(t, None)


def issue_ws_ticket() -> str:
    """Issue a secure, single-use, short-lived WebSocket connection ticket."""
    _prune_tickets()
    ticket = secrets.token_urlsafe(32)
    _TICKET_STORE[ticket] = time.time() + _TICKET_TTL_SECONDS
    return ticket


def verify_and_consume_ws_ticket(ticket: str) -> bool:
    """Verify and immediately consume a single-use WebSocket connection ticket."""
    _prune_tickets()
    if not ticket:
        return False
    expiry = _TICKET_STORE.pop(ticket, None)
    if expiry is None:
        return False
    return expiry >= time.time()


class TicketResponse(BaseModel):
    ticket: str
    expires_in: int


@router.post("/ws-ticket", response_model=TicketResponse)
async def request_ws_ticket(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """Issue a short-lived one-time ticket for WebSocket connection."""
    if SERVER_API_KEY:
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        elif x_api_key:
            token = x_api_key.strip()

        if not token or not hmac.compare_digest(token, SERVER_API_KEY):
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")

    ticket = issue_ws_ticket()
    return TicketResponse(ticket=ticket, expires_in=int(_TICKET_TTL_SECONDS))
