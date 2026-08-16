# security/credentials.py — Opaque Credential Storage & Reference Manager
"""
Opaque Credential Reference Manager for BR JARVIS MK37.
Ensures raw API keys, OAuth tokens, passwords, and device PINs are never passed
directly into LLM prompts or serialized into unbounded context memory.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.Credentials")

from brjarvis.core.paths import paths

CONFIG_DIR = paths.CONFIG_ROOT
CREDENTIALS_FILE = CONFIG_DIR / "credential_vault.json"


class CredentialVault:
    """Stores sensitive credentials referenced by opaque credential IDs."""

    def __init__(self, vault_path: Path = CREDENTIALS_FILE):
        self.vault_path = vault_path
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.vault_path.exists():
            try:
                self._cache = json.loads(self.vault_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Failed to read credential vault: %s", e)
                self._cache = {}

    def _save(self) -> None:
        try:
            self.vault_path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save credential vault: %s", e)

    def store_credential(self, credential_ref: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a secret under an opaque reference ID."""
        self._cache[credential_ref] = {
            "value": secret_value,
            "metadata": metadata or {},
        }
        self._save()
        logger.info("Credential stored for reference: %s", credential_ref)
        return credential_ref

    def get_credential(self, credential_ref: str) -> Optional[str]:
        """Retrieve raw secret for execution (internal tool use only)."""
        entry = self._cache.get(credential_ref)
        if entry:
            return entry.get("value")
        # Check environment variables fallback
        env_key = credential_ref.upper().replace("-", "_").replace(".", "_")
        return os.environ.get(env_key)

    def list_references(self) -> List[Dict[str, Any]]:
        """List metadata for stored credentials without exposing secret values."""
        results = []
        for ref, data in self._cache.items():
            results.append({
                "credential_ref": ref,
                "metadata": data.get("metadata", {}),
                "is_set": bool(data.get("value"))
            })
        return results

    def delete_credential(self, credential_ref: str) -> bool:
        if credential_ref in self._cache:
            del self._cache[credential_ref]
            self._save()
            return True
        return False


_vault_instance: Optional[CredentialVault] = None


def get_credential_vault() -> CredentialVault:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = CredentialVault()
    return _vault_instance
