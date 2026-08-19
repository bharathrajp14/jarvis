"""Canonical FastAPI control-plane package for BR-JARVIS."""

from __future__ import annotations


def create_app():
    """Import the application factory lazily to avoid import-time side effects."""
    from .server import create_app as factory

    return factory()


__all__ = ["create_app"]
