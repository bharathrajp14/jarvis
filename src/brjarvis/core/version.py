# core/version.py — Canonical Version Authority for BR JARVIS
"""
Single authoritative source of version and build metadata for BR JARVIS.
All CLI banners, Web UI indicators, API responses, health endpoints, package metadata,
and runtime logs must source version information exclusively from here.
"""
from __future__ import annotations

from typing import Any, Dict

__version__ = "41.0.0"
VERSION = __version__
BUILD = "2026-08-18"
CODENAME = "MARK XLI"
DESCRIPTION = "BR JARVIS — Cognitive Multi-Modal AI Operating System & Autonomous Controller"


def get_version() -> str:
    """Return the canonical version string."""
    return VERSION


def get_version_info() -> Dict[str, Any]:
    """Return structured version and release metadata."""
    return {
        "version": VERSION,
        "build": BUILD,
        "codename": CODENAME,
        "description": DESCRIPTION,
    }


def get_banner_info() -> str:
    """Return single-line formatted version banner."""
    return f"BR JARVIS v{VERSION} ({CODENAME}, Build {BUILD})"
