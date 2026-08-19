from __future__ import annotations

import logging
import os
from collections.abc import Iterable

from brjarvis.security.credentials import get_credential_vault

logger = logging.getLogger("JARVIS.Actions.Credentials")


def get_secret(reference: str, env_names: Iterable[str] = ()) -> str:
    """Return a secret from explicit environment names or the OS credential vault."""
    for env_name in env_names:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    try:
        return (get_credential_vault().get_credential(reference) or "").strip()
    except Exception as exc:
        logger.debug("Credential vault unavailable for %s: %s", reference, exc)
        return ""


def get_gemini_key() -> str:
    return get_secret("gemini-api-key", ("GEMINI_API_KEY", "GOOGLE_API_KEY"))


def get_openai_key() -> str:
    return get_secret("openai-api-key", ("OPENAI_API_KEY",))


def get_tavily_key() -> str:
    return get_secret("tavily-api-key", ("TAVILY_API_KEY",))
