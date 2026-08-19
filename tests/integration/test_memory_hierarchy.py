"""Integration tests for Multi-Tier Memory Subsystem (L1-L4)."""

from __future__ import annotations

import pytest

from brjarvis.memory.canonical_db import CanonicalDatabaseManager
from brjarvis.memory.vector_store import VectorMemory


@pytest.mark.integration
def test_vector_memory_search(tmp_path):
    """Verify vector memory store indexes and retrieves semantic documents."""
    store_dir = tmp_path / "vector_db"
    store_dir.mkdir(parents=True, exist_ok=True)
    vm = VectorMemory(persist_dir=str(store_dir))

    vm.add_memory("FastAPI web server routes on port 8000 with Three.js 3D galaxy visualization.")
    vm.add_memory("Career OS 7-factor ATS evaluation engine tailored for senior AI systems roles.")

    results = vm.search("FastAPI web server", top_k=1)
    assert len(results) > 0
    assert "FastAPI" in results[0]["text"] or "8000" in results[0]["text"]


@pytest.mark.integration
def test_canonical_db_operations(tmp_path):
    """Verify canonical SQLite database writes and reads records in WAL mode."""
    db_file = tmp_path / "test_canonical.db"
    db = CanonicalDatabaseManager(db_path=db_file)

    db.set_preference("theme", "cyberpunk_neon")
    assert db.get_preference("theme") == "cyberpunk_neon"
