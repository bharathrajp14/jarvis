# config/models.py — JARVIS MK37 Model Configuration (Gemini-Native)
"""
Central model configuration. Gemini is the primary backend.
Priority: ENV VARS > models.json > hardcoded defaults
"""
from __future__ import annotations

import os
import json
from pathlib import Path

_CONFIG_DIR  = Path(__file__).resolve().parent
_MODELS_JSON = _CONFIG_DIR / "models.json"

# ── Defaults (Gemini-first) ────────────────────────────────────────────────
_DEFAULTS = {
    "voice_live":       "gemini-3.5-flash",
    "voice_name":       "Charon",
    "gemini":           "gemini-3.5-flash",
    "gemini_code":      "gemini-3.6-flash-medium",
    "gemini_reasoning": "gemini-3.6-flash-high",
    "gemini_general":   "gemini-3.5-flash",
    "gemini_agent":     "gemini-3.6-flash-medium",
    "gemini_fast":      "gemini-3.6-flash-low",
    "gemini_vision":    "gemini-3.1-flash-image",
    "gemini_lite":      "gemini-3.1-flash-lite",
    "claude":           "claude-sonnet-4-6",
    "claude_opus":      "claude-opus-4-6-thinking",
    "gpt":              "gemini-3.5-flash",
    "gpt_mini":         "gemini-3.1-flash-lite",
    "gpt_4o":           "gemini-3.6-flash-high",
    "ollama":           "llama3.3",
    "nvidia":           "meta/llama-3.1-70b-instruct",
    "mistral":          "mistral-large-latest",
    "default_backend":  "gemini",
    "planner_model":    "gemini-3.6-flash-medium",
    "fast_model":       "gemini-3.5-flash",
    "openai_base_url":  "http://127.0.0.1:8045/v1",
    "openai_api_key":   "none",
    "openai_model":     "gemini-3.5-flash",
}


_ENV_MAP = {
    "JARVIS_MODEL_GEMINI":    "gemini",
    "JARVIS_MODEL_CLAUDE":    "claude",
    "JARVIS_MODEL_GPT":       "gpt",
    "JARVIS_MODEL_OLLAMA":    "ollama",
    "JARVIS_MODEL_NVIDIA":    "nvidia",
    "JARVIS_MODEL_MISTRAL":   "mistral",
    "JARVIS_MODEL_VOICE":     "voice_live",
    "JARVIS_VOICE_NAME":      "voice_name",
    "JARVIS_DEFAULT_BACKEND": "default_backend",
    "OPENAI_BASE_URL":        "openai_base_url",
    "OPENAI_MODEL":           "openai_model",
}

_cache: dict | None = None


def get_model_config(force_reload: bool = False) -> dict:
    global _cache
    if _cache is not None and not force_reload:
        return _cache.copy()

    config = dict(_DEFAULTS)

    # models.json overrides
    if _MODELS_JSON.exists():
        try:
            data = json.loads(_MODELS_JSON.read_text(encoding="utf-8"))
            for k, v in data.items():
                if not k.startswith("_") and isinstance(v, str) and v.strip():
                    config[k] = v.strip()
        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.info(f"{ f"[Config] Warning reading models.json: {e}" }" if isinstance(f"[Config] Warning reading models.json: {e}", str) else f"[Config] Warning reading models.json: {e}")
            else:
                import logging
                logging.getLogger(__name__).info(f"{ f"[Config] Warning reading models.json: {e}" }" if isinstance(f"[Config] Warning reading models.json: {e}", str) else f"[Config] Warning reading models.json: {e}")

    # ENV overrides (highest priority)
    for env_key, cfg_key in _ENV_MAP.items():
        val = os.environ.get(env_key, "").strip()
        if val:
            config[cfg_key] = val

    # Always ensure Gemini stays default if configured
    if config.get("default_backend") not in ("gemini", "claude", "gpt", "ollama", "nvidia", "mistral"):
        config["default_backend"] = "gemini"

    _cache = config
    return config.copy()


def clear_model_config_cache():
    """Clear cached model configuration to force a reload on setting changes."""
    global _cache
    _cache = None


def get_model(backend: str) -> str:
    return get_model_config().get(backend, _DEFAULTS.get(backend, ""))


def get_model_for_task(
    task_type: str | None = None,
    messages: list[dict] | None = None,
    system: str = ""
) -> str:
    """
    Intelligently select the best specialized Gemini model for a given task type and/or prompt payload complexity.
    """
    if messages is not None:
        try:
            from config.complexity_router import select_model_for_prompt
            return select_model_for_prompt(messages=messages, system=system, task_type=task_type)
        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.warning(f"{ f"[Config] Complexity router error: {e}" }" if isinstance(f"[Config] Complexity router error: {e}", str) else f"[Config] Complexity router error: {e}")
            else:
                import logging
                logging.getLogger(__name__).warning(f"{ f"[Config] Complexity router error: {e}" }" if isinstance(f"[Config] Complexity router error: {e}", str) else f"[Config] Complexity router error: {e}")

    cfg = get_model_config()
    task = (task_type or "general").lower()

    if task in ("code", "coding", "architecture", "refactor", "debug"):
        return cfg.get("gemini_code", "gemini-3.1-pro-high")
    elif task in ("reasoning", "math", "logic", "audit", "security"):
        return cfg.get("gemini_reasoning", "gemini-3.1-pro-high")
    elif task in ("agent", "planner", "workflow", "dag", "multi_step"):
        return cfg.get("gemini_agent", "gemini-3.6-flash-medium")
    elif task in ("vision", "ocr", "screen", "image", "ui_scan"):
        return cfg.get("gemini_vision", "gemini-3.1-flash-image")
    elif task in ("fast", "status", "quick", "summary", "log"):
        return cfg.get("gemini_fast", "gemini-3-flash")
    elif task in ("lite", "autocomplete", "prefix", "token"):
        return cfg.get("gemini_lite", "gemini-3.1-flash-lite")
    else:
        return cfg.get("gemini_general", "gemini-3.6-flash-high")


def ensure_models_json():
    """Create models.json with defaults if it doesn't exist."""
    if not _MODELS_JSON.exists():
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = dict(_DEFAULTS)
        data["_comment"] = (
            "Edit this file to change models. JARVIS reads it on every boot. "
            "Gemini is the only required backend. Set GEMINI_API_KEY in .env"
        )
        _MODELS_JSON.write_text(json.dumps(data, indent=4), encoding="utf-8")
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[Config] Created default models.json at {_MODELS_JSON}" }" if isinstance(f"[Config] Created default models.json at {_MODELS_JSON}", str) else f"[Config] Created default models.json at {_MODELS_JSON}")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[Config] Created default models.json at {_MODELS_JSON}" }" if isinstance(f"[Config] Created default models.json at {_MODELS_JSON}", str) else f"[Config] Created default models.json at {_MODELS_JSON}")


ensure_models_json()

