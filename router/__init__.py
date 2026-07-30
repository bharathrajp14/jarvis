# router/__init__.py — JARVIS MK37 Router Package
"""
Re-exports AgentRouter and AgentProfile for unified import.
"""
from __future__ import annotations

from router.core import AgentRouter, AgentProfile, ROUTING_RULES, load_available_backends

__all__ = [
    "AgentRouter",
    "AgentProfile",
    "ROUTING_RULES",
    "load_available_backends",
]
