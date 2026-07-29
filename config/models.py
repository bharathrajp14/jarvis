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
    "voice_live":       "models/gemini-3.1-flash-live-preview",
    "voice_name":       "Charon",
    "gemini":           "gemini-3-flash",
    "gemini_code":      "gemini-3-flash",
    "gemini_reasoning": "gemini-3.6-flash-medium",
    "gemini_general":   "gemini-3-flash",
    "gemini_agent":     "gemini-3-flash",
    "gemini_fast":      "gemini-3-flash",
    "gemini_vision":    "gemini-3.1-flash-image",
    "gemini_lite":      "gemini-3-flash",
    "claude":           "gemini-3-flash",
    "gpt":              "gemini-3-flash",
    "gpt_mini":         "gemini-3-flash",
    "gpt_4o":           "gemini-3.6-flash-medium",
    "ollama":           "llama3.3",
    "nvidia":           "meta/llama-3.1-70b-instruct",
    "mistral":          "mistral-large-latest",
    "default_backend":  "gpt",
    "planner_model":    "gemini-3-flash",
    "fast_model":       "gemini-3-flash",
    "openai_base_url":  "http://127.0.0.1:8045/v1",
    "openai_api_key":   "sk-1bbc6e7e09c447e699690ffadb469f89",
    "openai_model":     "gemini-3-flash",
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
            print(f"[Config] Warning reading models.json: {e}")

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


def get_model_for_task(task_type: str) -> str:
    """
    Intelligently select the best specialized Gemini model for a given task type.
    
    Task categories:
      - 'code' / 'coding' / 'architecture' -> gemini-3.1-pro-high
      - 'reasoning' / 'math' / 'logic'    -> gemini-3.1-pro-high
      - 'agent' / 'planner' / 'workflow'  -> gemini-3-flash-agent
      - 'vision' / 'ocr' / 'screen'       -> gemini-3.1-flash-image
      - 'fast' / 'status' / 'quick'       -> gemini-3.5-flash-low
      - 'lite' / 'autocomplete'           -> gemini-3.1-flash-lite
      - default / 'general' / 'search'    -> gemini-3-flash
    """
    cfg = get_model_config()
    task = (task_type or "general").lower()

    if task in ("code", "coding", "architecture", "refactor", "debug"):
        return cfg.get("gemini_code", "gemini-pro-agent")
    elif task in ("reasoning", "math", "logic", "audit", "security"):
        return cfg.get("gemini_reasoning", "gemini-pro-agent")
    elif task in ("agent", "planner", "workflow", "dag", "multi_step"):
        return cfg.get("gemini_agent", "gemini-3-flash-agent")
    elif task in ("vision", "ocr", "screen", "image", "ui_scan"):
        return cfg.get("gemini_vision", "gemini-3-flash")
    elif task in ("fast", "status", "quick", "summary", "log"):
        return cfg.get("gemini_fast", "gemini-3.5-flash-low")
    elif task in ("lite", "autocomplete", "prefix", "token"):
        return cfg.get("gemini_lite", "gemini-3.5-flash-extra-low")
    else:
        return cfg.get("gemini_general", "gemini-3-flash")


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
        print(f"[Config] Created default models.json at {_MODELS_JSON}")


ensure_models_json()

