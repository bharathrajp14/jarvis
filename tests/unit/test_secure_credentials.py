from __future__ import annotations

import json

import pytest

from brjarvis.security.credentials import CredentialVault


class MemorySecretBackend:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.values[(service_name, username)] = password

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.values.get((service_name, username))

    def delete_password(self, service_name: str, username: str) -> None:
        self.values.pop((service_name, username), None)


@pytest.mark.unit
def test_credential_vault_keeps_secret_out_of_metadata_file(tmp_path):
    backend = MemorySecretBackend()
    vault_path = tmp_path / "credential_vault.json"
    vault = CredentialVault(vault_path=vault_path, backend=backend, service_name="test-brjarvis")

    reference = vault.store_credential("github-token", "super-secret-value", {"provider": "github"})

    assert reference == "github-token"
    assert vault.get_credential(reference) == "super-secret-value"
    serialized = vault_path.read_text(encoding="utf-8")
    assert "super-secret-value" not in serialized
    assert json.loads(serialized) == {
        "github-token": {"metadata": {"provider": "github"}}
    }
    assert vault.list_references() == [
        {
            "credential_ref": "github-token",
            "metadata": {"provider": "github"},
            "is_set": True,
        }
    ]


@pytest.mark.unit
def test_credential_vault_migrates_legacy_plaintext(tmp_path):
    backend = MemorySecretBackend()
    vault_path = tmp_path / "credential_vault.json"
    vault_path.write_text(
        json.dumps({"legacy-ref": {"value": "legacy-secret", "metadata": {"source": "legacy"}}}),
        encoding="utf-8",
    )

    vault = CredentialVault(vault_path=vault_path, backend=backend, service_name="test-brjarvis")

    assert vault.get_credential("legacy-ref") == "legacy-secret"
    assert "legacy-secret" not in vault_path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_credential_delete_requires_backend_success(tmp_path):
    backend = MemorySecretBackend()
    vault = CredentialVault(vault_path=tmp_path / "credential_vault.json", backend=backend)
    vault.store_credential("delete-me", "secret")

    assert vault.delete_credential("delete-me") is True
    assert vault.get_credential("delete-me") is None
    assert vault.list_references() == []
