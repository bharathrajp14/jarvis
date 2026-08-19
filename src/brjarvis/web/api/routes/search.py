# api/routes/search.py — Global Unified Workspace Search API
from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from brjarvis.memory.workspace_store import get_workspace_store

logger = logging.getLogger("JARVIS.API.Search")
router = APIRouter(tags=["Search"])


@router.get("/api/search")
async def global_search(
    q: str = Query(..., description="Query search string"),
    limit: int = Query(25, ge=1, le=100),
):
    """Unified search across all entity types (conversations, messages, projects, tasks, artifacts, files)."""
    store = get_workspace_store()
    results = store.search_all(query_str=q, limit=limit)
    return {"query": q, "total": len(results), "results": results}
