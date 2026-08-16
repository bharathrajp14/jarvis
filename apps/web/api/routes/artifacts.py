# api/routes/artifacts.py — Workspace Artifacts & Provenance Endpoints
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from brjarvis.agent.artifacts import ArtifactManager
from brjarvis.memory.workspace_store import get_workspace_store

logger = logging.getLogger("JARVIS.API.Artifacts")
router = APIRouter(tags=["Artifacts"])


class VerifyArtifactRequest(BaseModel):
    verified: bool = True


@router.get("/api/artifacts")
async def list_artifacts(
    conversation_id: Optional[str] = None,
    task_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
):
    """List artifacts with provenance and filter criteria."""
    store = get_workspace_store()
    artifacts = store.list_artifacts(
        conversation_id=conversation_id,
        task_id=task_id,
        project_id=project_id,
        limit=limit,
    )
    return {"total": len(artifacts), "artifacts": [a.to_dict() for a in artifacts]}


@router.get("/api/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Get artifact record and provenance details."""
    store = get_workspace_store()
    art = store.get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return art.to_dict()


@router.get("/api/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str):
    """Download the actual artifact file securely."""
    store = get_workspace_store()
    art = store.get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact record not found")

    file_path = Path(art.host_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file does not exist on disk")

    return FileResponse(
        path=str(file_path),
        filename=art.filename,
        media_type=art.mime_type or "application/octet-stream",
    )


@router.get("/api/artifacts/{artifact_id}/preview")
async def preview_artifact(artifact_id: str):
    """Get preview content for text/markdown/code/json artifacts."""
    store = get_workspace_store()
    art = store.get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    file_path = Path(art.host_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk")

    ext = file_path.suffix.lower()
    text_extensions = {".md", ".markdown", ".txt", ".json", ".py", ".html", ".csv", ".tsv", ".xml", ".yaml", ".yml", ".log", ".css", ".js"}

    if ext in text_extensions:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return {
                "artifact_id": art.artifact_id,
                "filename": art.filename,
                "is_text": True,
                "content": content[:50000],
                "truncated": len(content) > 50000,
                "mime_type": art.mime_type,
            }
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}

    return {
        "artifact_id": art.artifact_id,
        "filename": art.filename,
        "is_text": False,
        "mime_type": art.mime_type,
        "download_url": f"/api/artifacts/{art.artifact_id}/download",
    }


@router.post("/api/artifacts/{artifact_id}/verify")
async def verify_artifact(artifact_id: str, req: VerifyArtifactRequest):
    """Update verification status of an artifact."""
    store = get_workspace_store()
    success = store.verify_artifact(artifact_id, verified=req.verified)
    if not success:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"status": "success", "artifact_id": artifact_id, "verification_status": "VERIFIED" if req.verified else "FAILED"}
