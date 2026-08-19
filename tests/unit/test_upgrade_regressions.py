from __future__ import annotations

import asyncio
import time
import typing
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from brjarvis.actions import web_search
from brjarvis.career.ats_engine.scorer import ATSEngine
from brjarvis.memory import config_manager, persistent_store
from brjarvis.tools.files import FileManager
from brjarvis.tools.runtime import ToolRuntime
from brjarvis.tools.sandbox_process import SandboxedProcessRunner
from brjarvis.web.api.routes import artifacts as artifact_routes


@pytest.mark.unit
def test_artifact_routes_reject_existing_file_outside_approved_roots(tmp_path, monkeypatch):
    artifact_root = tmp_path / "artifacts"
    workspace_root = tmp_path / "workspace"
    artifact_root.mkdir()
    workspace_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("must not be served", encoding="utf-8")

    monkeypatch.setattr(artifact_routes.paths, "ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(artifact_routes.paths, "WORKSPACE_ROOT", workspace_root)

    fake_artifact = SimpleNamespace(
        artifact_id="art_outside",
        filename="outside.txt",
        host_path=str(outside_file),
        mime_type="text/plain",
        to_dict=lambda: {
            "artifact_id": "art_outside",
            "filename": "outside.txt",
            "host_path": str(outside_file),
            "sandbox_path": "C:/sensitive/source.py",
        },
    )

    class FakeStore:
        def get_artifact(self, artifact_id):
            return fake_artifact if artifact_id == "art_outside" else None

    monkeypatch.setattr(artifact_routes, "get_workspace_store", lambda: FakeStore())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(artifact_routes.download_artifact("art_outside"))
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(artifact_routes.preview_artifact("art_outside"))
    assert exc_info.value.status_code == 404

    payload = asyncio.run(artifact_routes.get_artifact("art_outside"))
    assert "host_path" not in payload
    assert "sandbox_path" not in payload


@pytest.mark.unit
def test_artifact_routes_serve_file_inside_approved_artifact_root(tmp_path, monkeypatch):
    artifact_root = tmp_path / "artifacts"
    workspace_root = tmp_path / "workspace"
    artifact_root.mkdir()
    workspace_root.mkdir()
    valid_file = artifact_root / "result.txt"
    valid_file.write_text("approved", encoding="utf-8")

    monkeypatch.setattr(artifact_routes.paths, "ARTIFACT_ROOT", artifact_root)
    monkeypatch.setattr(artifact_routes.paths, "WORKSPACE_ROOT", workspace_root)

    fake_artifact = SimpleNamespace(
        artifact_id="art_valid",
        filename="result.txt",
        host_path=str(valid_file),
        mime_type="text/plain",
        to_dict=lambda: {"artifact_id": "art_valid", "filename": "result.txt"},
    )

    class FakeStore:
        def get_artifact(self, artifact_id):
            return fake_artifact

    monkeypatch.setattr(artifact_routes, "get_workspace_store", lambda: FakeStore())
    response = asyncio.run(artifact_routes.download_artifact("art_valid"))
    assert Path(response.path).resolve() == valid_file.resolve()


@pytest.mark.unit
def test_sandbox_runner_executes_basic_python_without_missing_sanitizer():
    result = SandboxedProcessRunner().execute(
        "print('sandbox-ok')",
        lang="python",
        timeout=5,
        auto_export_artifacts=False,
    )
    assert result["success"] is True
    assert "sandbox-ok" in result["stdout"]


@pytest.mark.unit
def test_sync_tool_timeout_is_enforced():
    runtime = ToolRuntime()

    def slow_handler(_args):
        time.sleep(0.4)
        return "late"

    runtime.register_tool(
        name="upgrade_sync_timeout",
        description="Regression test for synchronous timeout enforcement",
        handler=slow_handler,
        is_read_only=True,
        timeout_sec=0.05,
    )

    result = asyncio.run(runtime.execute_tool_async("upgrade_sync_timeout", {}))
    assert result.status.value == "TIMEOUT"


@pytest.mark.unit
def test_legacy_config_status_and_ats_type_hints_are_runtime_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(config_manager, "CONFIG_FILE", tmp_path / "api_keys.json")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    class EmptyVault:
        def get_credential(self, _reference):
            return None

    monkeypatch.setattr(config_manager, "get_credential_vault", lambda: EmptyVault())
    assert config_manager.is_configured() is False

    hints = typing.get_type_hints(ATSEngine.evaluate_resume)
    assert "resume" in hints
    assert hints["resume"] is not None


@pytest.mark.unit
def test_web_search_tavily_fallback_without_credentials_is_safe(monkeypatch, tmp_path):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(web_search.paths, "CONFIG_ROOT", tmp_path)
    assert web_search._tavily_search("no credentials", max_results=1) == []


@pytest.mark.unit
def test_legacy_config_save_never_serializes_provider_secret(monkeypatch, tmp_path):
    class FakeVault:
        def store_credential(self, reference, secret_value, metadata=None):
            assert reference == "gemini-api-key"
            assert secret_value == "secret-value"

        def get_credential(self, _reference):
            return None

    config_file = tmp_path / "api_keys.json"
    monkeypatch.setattr(config_manager, "CONFIG_FILE", config_file)
    monkeypatch.setattr(config_manager, "get_credential_vault", lambda: FakeVault())

    config_manager.save_api_keys("secret-value")
    content = config_file.read_text(encoding="utf-8")
    assert "secret-value" not in content
    assert '"gemini_credential_ref": "gemini-api-key"' in content


@pytest.mark.unit
def test_start_web_forwards_explicit_host_and_port(monkeypatch):
    import start

    seen = {}
    monkeypatch.setattr(start, "launch_web_server", lambda **kwargs: seen.update(kwargs))
    assert start.main(["web", "--host", "0.0.0.0", "--port", "9999", "--no-open"]) == 0
    assert seen == {"open_url": None, "host": "0.0.0.0", "port": 9999}


@pytest.mark.unit
def test_file_manager_rejects_temporary_root_escape(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    temp_root = tmp_path / "temp"
    workspace.mkdir()
    temp_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    monkeypatch.setattr("brjarvis.tools.files.paths.TEMP_ROOT", temp_root)
    manager = FileManager(workspace=workspace)

    with pytest.raises(Exception) as exc_info:
        manager.read("/tmp/../outside.txt")
    assert "outside" in str(exc_info.value).lower() or "temporary" in str(exc_info.value).lower()


@pytest.mark.unit
def test_strict_memory_save_reports_vector_sync_failure(tmp_path, monkeypatch):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    monkeypatch.setattr(persistent_store, "get_memory_dir", lambda _scope: memory_dir)
    monkeypatch.setattr(persistent_store, "_rewrite_index", lambda _scope: None)
    monkeypatch.setattr(
        persistent_store,
        "_sync_to_vector",
        lambda _entry: (_ for _ in ()).throw(RuntimeError("vector unavailable")),
    )

    entry = persistent_store.MemoryEntry(
        name="strict-test",
        description="regression",
        type="reference",
        content="safe content",
    )
    with pytest.raises(persistent_store.MemoryPersistenceError):
        persistent_store.save_memory(entry, strict=True)
