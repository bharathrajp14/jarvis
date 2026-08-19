# src/brjarvis/config/__init__.py
"""Configuration management and system settings for BR JARVIS."""

from __future__ import annotations

import json
import os
from pathlib import Path

from brjarvis.core.paths import paths

_CONFIG_PATH = paths.CONFIG_ROOT / "api_keys.json"


def get_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_gemini_api_key(required: bool = False) -> str:
    """Centralized loader for Gemini / Google API Key from env or config/api_keys.json."""
    for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(env, "").strip()
        if val:
            return val

    cfg = get_config()
    key = str(cfg.get("gemini_api_key", "")).strip()
    if key:
        return key

    if required:
        raise ValueError(
            "No Gemini API key found.\nSet GEMINI_API_KEY env var OR add 'gemini_api_key' to config/api_keys.json"
        )
    return ""


def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    return get_config().get("os_system", "windows").lower()


def is_windows() -> bool:
    return get_os() == "windows"


def is_mac() -> bool:
    return get_os() == "mac"


def is_linux() -> bool:
    return get_os() == "linux"
