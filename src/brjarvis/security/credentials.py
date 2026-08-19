# security/credentials.py — Opaque Credential Storage & Reference Manager
"""Secure credential references backed by the operating-system keyring.

Raw secrets are never written to project JSON files. The JSON vault contains
metadata only; secret values live in the platform credential store exposed by
``keyring``. A backend may be injected for deterministic tests.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.Credentials")

CONFIG_DIR = paths.CONFIG_ROOT
CREDENTIALS_FILE = CONFIG_DIR / "credential_vault.json"
_KEYRING_SERVICE = "brjarvis"


class SecretBackend(Protocol):
    """Minimal secret-store contract used by ``CredentialVault``."""

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def get_password(self, service_name: str, username: str) -> Optional[str]: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class KeyringSecretBackend:
    """Typed adapter around the optional keyring module API."""

    def __init__(self, keyring_module: Any):
        self._keyring = keyring_module

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._keyring.set_password(service_name, username, password)

    def get_password(self, service_name: str, username: str) -> Optional[str]:
        return self._keyring.get_password(service_name, username)

    def delete_password(self, service_name: str, username: str) -> None:
        self._keyring.delete_password(service_name, username)


def _default_secret_backend() -> SecretBackend:
    try:
        import keyring
        from keyring.errors import NoKeyringError

        backend = keyring.get_keyring()
        priority = getattr(backend, "priority", 0)
        if priority is None or float(priority) <= 0:
            raise NoKeyringError("No secure operating-system keyring backend is available")
        return KeyringSecretBackend(keyring)
    except (ImportError, RuntimeError, ValueError) as exc:
        raise RuntimeError(
            "Secure credential storage is unavailable. Install the 'keyring' dependency "
            "and configure an operating-system credential backend."
        ) from exc


class CredentialVault:
    """Store secret values in an OS keyring and expose opaque references only."""

    def __init__(
        self,
        vault_path: Path = CREDENTIALS_FILE,
        backend: Optional[SecretBackend] = None,
        service_name: str = _KEYRING_SERVICE,
    ):
        self.vault_path = Path(vault_path)
        self.service_name = service_name
        self._backend = backend
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    @property
    def backend(self) -> SecretBackend:
        if self._backend is None:
            self._backend = _default_secret_backend()
        return self._backend

    def _load(self) -> None:
        if not self.vault_path.exists():
            return
        try:
            raw = json.loads(self.vault_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("credential metadata must be a JSON object")
            self._cache = {}
            legacy_secrets: Dict[str, str] = {}
            for reference, entry in raw.items():
                if not isinstance(entry, dict):
                    continue
                value = entry.get("value")
                if isinstance(value, str) and value:
                    legacy_secrets[str(reference)] = value
                self._cache[str(reference)] = {"metadata": dict(entry.get("metadata") or {})}
            if legacy_secrets:
                self._migrate_legacy_plaintext(legacy_secrets)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.error("Failed to read credential metadata: %s", exc)
            self._cache = {}

    def _migrate_legacy_plaintext(self, legacy_secrets: Dict[str, str]) -> None:
        """Move legacy JSON values into the OS keyring before sanitizing metadata."""
        try:
            for reference, value in legacy_secrets.items():
                self.backend.set_password(self.service_name, reference, value)
            self._save()
            logger.warning("Migrated %d legacy credential values into the OS keyring", len(legacy_secrets))
        except Exception as exc:
            raise RuntimeError(
                "Legacy plaintext credentials were detected but could not be migrated securely. "
                "Configure an OS keyring before using the credential vault."
            ) from exc

    def _save(self) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._cache, indent=2, sort_keys=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.vault_path.name}.",
            suffix=".tmp",
            dir=str(self.vault_path.parent),
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                logger.debug("Unable to apply POSIX metadata permissions to %s", temp_path)
            temp_path.replace(self.vault_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def store_credential(
        self,
        credential_ref: str,
        secret_value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a secret under an opaque reference without serializing its value."""
        reference = credential_ref.strip()
        if not reference:
            raise ValueError("credential_ref is required")
        if not secret_value:
            raise ValueError("secret_value is required")
        self.backend.set_password(self.service_name, reference, secret_value)
        self._cache[reference] = {"metadata": dict(metadata or {})}
        self._save()
        logger.info("Credential stored for opaque reference: %s", reference)
        return reference

    def get_credential(self, credential_ref: str) -> Optional[str]:
        """Retrieve a secret internally from keyring or an explicit environment fallback."""
        reference = credential_ref.strip()
        if not reference:
            return None
        try:
            value = self.backend.get_password(self.service_name, reference)
        except RuntimeError:
            value = None
        if value:
            return value
        env_key = reference.upper().replace("-", "_").replace(".", "_")
        return os.environ.get(env_key)

    def list_references(self) -> List[Dict[str, Any]]:
        """List credential metadata without retrieving or exposing secret values."""
        results: List[Dict[str, Any]] = []
        for reference, data in self._cache.items():
            try:
                is_set = bool(self.backend.get_password(self.service_name, reference))
            except RuntimeError:
                is_set = False
            results.append(
                {
                    "credential_ref": reference,
                    "metadata": dict(data.get("metadata") or {}),
                    "is_set": is_set,
                }
            )
        return results

    def delete_credential(self, credential_ref: str) -> bool:
        reference = credential_ref.strip()
        if reference not in self._cache:
            return False
        try:
            self.backend.delete_password(self.service_name, reference)
        except Exception as exc:
            logger.warning("Unable to delete credential '%s' from keyring: %s", reference, exc)
            return False
        del self._cache[reference]
        self._save()
        return True


_vault_instance: Optional[CredentialVault] = None


def get_credential_vault() -> CredentialVault:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = CredentialVault()
    return _vault_instance
