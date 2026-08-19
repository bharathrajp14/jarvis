# src/brjarvis/config/model_loader.py
"""Central model configuration loader for BR JARVIS.
Reads config/models.json and provides defaults if it doesn't exist.
"""

from __future__ import annotations

import json
import logging

from brjarvis.core.paths import paths

logger = logging.getLogger(__name__)

_CONFIG_DIR = paths.CONFIG_ROOT
_MODELS_FILE = _CONFIG_DIR / "models.json"

DEFAULTS = {
    "voice_live": "gemini-3.6-flash-tiered",
    "voice_name": "Charon",
    "claude": "gemini-3-flash-agent",
    "gpt": "gemini-3-flash-agent",
    "gemini": "gemini-3-flash-agent",
    "gemini_code": "gemini-3-flash-agent",
    "gemini_reasoning": "gemini-3-flash-agent",
    "gemini_general": "gemini-3-flash-agent",
    "gemini_agent": "gemini-3-flash-agent",
    "gemini_pro_agent": "gemini-3-flash-agent",
    "gemini_fast": "gemini-3.5-flash-low",
    "gemini_vision": "gemini-3.1-flash-image",
    "gemini_lite": "gemini-3.5-flash-extra-low",
    "ollama": "llama3.3",
    "nvidia": "meta/llama-3.1-70b-instruct",
    "default_backend": "gpt",
    "disable_gemini": True,
}


def load_models() -> dict:
    """
    Load model configuration from config/models.json.
    Creates the file with defaults if it doesn't exist.
    """
    if not _MODELS_FILE.exists():
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _MODELS_FILE.write_text(
            json.dumps(DEFAULTS, indent=4),
            encoding="utf-8",
        )
        logger.info(f"[CONFIG] Created default models.json at {_MODELS_FILE}")
        return DEFAULTS.copy()

    try:
        data = json.loads(_MODELS_FILE.read_text(encoding="utf-8"))
        # Merge with defaults so new keys are always present
        merged = {**DEFAULTS, **data}
        return merged
    except Exception as e:
        logger.warning(f"[CONFIG] Error reading models.json: {e} — using defaults")
        return DEFAULTS.copy()


def save_models(models: dict):
    """Save updated model configuration back to disk."""
    # Remove internal comment keys
    clean = {k: v for k, v in models.items() if not k.startswith("_")}
    clean["_comment"] = "Edit this file to change models. JARVIS reads it on every boot."
    _MODELS_FILE.write_text(
        json.dumps(clean, indent=4),
        encoding="utf-8",
    )


# Module-level convenience: load once on import
MODELS = load_models()
