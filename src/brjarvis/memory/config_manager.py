from __future__ import annotations

import json
import logging
import os
from typing import Any

from brjarvis.core.paths import paths
from brjarvis.security.credentials import get_credential_vault

logger = logging.getLogger(__name__)

BASE_DIR = paths.PROJECT_ROOT
CONFIG_DIR = paths.CONFIG_ROOT
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

_SECRET_FIELDS = {
    "gemini_api_key": "gemini-api-key",
    "GEMINI_API_KEY": "gemini-api-key",
    "openai_api_key": "openai-api-key",
    "OPENAI_API_KEY": "openai-api-key",
    "tavily_api_key": "tavily-api-key",
    "TAVILY_API_KEY": "tavily-api-key",
}


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def _read_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to load configuration metadata: %s", exc)
        return {}


def _write_config(data: dict[str, Any]) -> None:
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _migrate_legacy_secrets(data: dict[str, Any]) -> dict[str, Any]:
    """Move legacy JSON secrets to the OS vault and return sanitized metadata."""
    sanitized = dict(data)
    migrated = 0
    for field, reference in _SECRET_FIELDS.items():
        value = sanitized.pop(field, None)
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            get_credential_vault().store_credential(
                reference,
                value.strip(),
                metadata={"migrated_from": field, "source": "legacy_config"},
            )
            sanitized[f"{reference}_ref"] = reference
            migrated += 1
        except Exception as exc:
            logger.error("Unable to migrate legacy credential %s securely: %s", field, exc)
            # Do not return the secret to callers. Leave the on-disk file untouched
            # so a later run with a configured keyring can complete migration.
    if migrated:
        try:
            _write_config(sanitized)
            logger.warning("Migrated %d legacy credential value(s) to the OS vault", migrated)
        except OSError as exc:
            logger.error("Credential migration succeeded but metadata cleanup failed: %s", exc)
    return sanitized


def save_api_keys(gemini_api_key: str) -> None:
    """Store a Gemini credential in the OS vault; JSON receives only a reference."""
    value = gemini_api_key.strip()
    if not value:
        raise ValueError("gemini_api_key is required")
    reference = "gemini-api-key"
    get_credential_vault().store_credential(
        reference,
        value,
        metadata={"provider": "gemini", "source": "config_manager"},
    )
    data = _migrate_legacy_secrets(_read_config())
    data.pop("gemini_api_key", None)
    data.pop("GEMINI_API_KEY", None)
    data["gemini_credential_ref"] = reference
    _write_config(data)


def load_api_keys() -> dict[str, Any]:
    """Return configuration metadata without exposing raw credential values."""
    return _migrate_legacy_secrets(_read_config())


def get_gemini_key() -> str | None:
    """Return the Gemini credential from environment or the OS vault."""
    value = os.environ.get("GEMINI_API_KEY", "").strip()
    if value:
        return value
    try:
        return get_credential_vault().get_credential("gemini-api-key")
    except Exception as exc:
        logger.debug("Gemini credential vault unavailable: %s", exc)
        return None


def is_configured() -> bool:
    """Return whether a usable provider credential is available."""
    candidates = (
        get_gemini_key(),
        os.environ.get("OPENAI_API_KEY"),
        os.environ.get("TAVILY_API_KEY"),
    )
    if any(isinstance(value, str) and len(value.strip()) > 5 for value in candidates):
        return True
    try:
        vault = get_credential_vault()
        return any(bool(vault.get_credential(reference)) for reference in ("openai-api-key", "tavily-api-key"))
    except Exception:
        return False


def get_assistant_name() -> str:
    """Return the configured assistant name, or 'JARVIS' if not set."""
    return str(load_api_keys().get("assistant_name", "JARVIS") or "JARVIS")


def get_user_name() -> str:
    """Return the configured user name for addressing."""
    return str(load_api_keys().get("user_name", "") or "")


def save_assistant_config(assistant_name: str, user_name: str) -> None:
    """Persist assistant and user preferences without touching credentials."""
    data = load_api_keys()
    data["assistant_name"] = assistant_name.strip() or "JARVIS"
    data["user_name"] = user_name.strip()
    _write_config(data)


def get_brief_enabled() -> bool:
    return bool(load_api_keys().get("morning_brief_enabled", True))


def save_brief_enabled(enabled: bool) -> None:
    data = load_api_keys()
    data["morning_brief_enabled"] = bool(enabled)
    _write_config(data)
