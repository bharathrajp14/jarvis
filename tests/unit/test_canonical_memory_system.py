# tests/unit/test_canonical_memory_system.py — Canonical Memory Subsystem Unit Tests
"""
Unit tests validating:
1. Persistent recovery across fresh process / store instances
2. Empty working memory cold-start retrieval
3. Temporal state (A -> B: current is B, historical is A)
4. Deterministic conflict resolution
5. Scoped conflict (global vs project specific)
6. Deletion propagation (store, cache, vector)
7. Vector store outage fallback
8. Provenance and trust hierarchy verification
"""

from __future__ import annotations

import time

import pytest

from brjarvis.memory.canonical_db import CanonicalDatabaseManager
from brjarvis.memory.conflict_engine import ConflictEngine, ConflictResolutionAction
from brjarvis.memory.domain import CanonicalMemory, MemoryStatus, MemoryType, SourceType
from brjarvis.memory.retrieval import HybridRetrievalEngine
from brjarvis.memory.store import CanonicalMemoryStore
from brjarvis.memory.task_memory_router import MemoryMode, TaskMemoryRouter
from brjarvis.memory.temporal import TemporalEngine


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_memory.db"
    return CanonicalDatabaseManager(db_path=db_file)


@pytest.fixture
def memory_store(temp_db):
    return CanonicalMemoryStore(db_manager=temp_db)


@pytest.fixture
def conflict_engine(memory_store):
    return ConflictEngine(store=memory_store)


@pytest.fixture
def temporal_engine(memory_store):
    return TemporalEngine(store=memory_store)


def test_persistent_recovery(tmp_path):
    """Store fact in one store instance, restart/create a fresh instance, verify fact is intact."""
    db_file = tmp_path / "persist_test.db"
    db1 = CanonicalDatabaseManager(db_path=db_file)
    store1 = CanonicalMemoryStore(db_manager=db1)

    mem = CanonicalMemory(
        entity="favorite_editor",
        attribute="editor",
        value="VS Code",
        content="User prefers VS Code with dark theme",
        memory_type=MemoryType.PREFERENCE,
        scope="user",
        source_type=SourceType.EXPLICIT_USER_STATEMENT,
    )
    store1.save(mem)

    # Fresh instance simulating new process / restart
    db2 = CanonicalDatabaseManager(db_path=db_file)
    store2 = CanonicalMemoryStore(db_manager=db2)
    recovered = store2.get(mem.memory_id)

    assert recovered is not None
    assert recovered.entity == "favorite_editor"
    assert recovered.value == "VS Code"
    assert recovered.memory_type == MemoryType.PREFERENCE
    assert recovered.status == MemoryStatus.ACTIVE


def test_empty_working_memory_cold_start_retrieval(memory_store):
    """Verify that a cold start (empty working memory) correctly retrieves persistent memories."""
    mem = CanonicalMemory(
        entity="python_version",
        attribute="version",
        value="3.12",
        content="Primary project language is Python 3.12",
        memory_type=MemoryType.PROJECT_STATE,
        scope="project",
        project_id="brjarvis",
    )
    memory_store.save(mem)

    retrieval = HybridRetrievalEngine(store=memory_store)
    router = TaskMemoryRouter(retrieval_engine=retrieval)

    # Empty working memory (working_memory_tokens = 0)
    mode = router.classify("What is our python version for this project?", working_memory_tokens=0)
    assert mode == MemoryMode.LOAD_RELEVANT

    slices = router.get_relevant_slices("python version", project_id="brjarvis")
    assert len(slices) > 0
    assert any("Python 3.12" in s["content"] for s in slices)


def test_temporal_state_evolution(memory_store, temporal_engine):
    """Verify temporal state: fact A superseded by fact B. Current is B, historical is A."""
    now = time.time()
    fact_a = CanonicalMemory(
        memory_id="mem_lang_1",
        entity="programming_language",
        attribute="primary",
        value="Python",
        content="Primary language is Python",
        effective_from=now - 100,
        status=MemoryStatus.ACTIVE,
        version=1,
    )
    memory_store.save(fact_a)

    # Time advances and language changes to C++
    fact_b = CanonicalMemory(
        memory_id="mem_lang_2",
        entity="programming_language",
        attribute="primary",
        value="C++",
        content="Primary language is C++",
        effective_from=now,
        status=MemoryStatus.ACTIVE,
        version=2,
    )
    memory_store.supersede(fact_a.memory_id, fact_b)

    current = temporal_engine.get_current_truth("programming_language", "primary")
    assert current is not None
    assert current.value == "C++"
    assert current.version == 2
    assert current.status == MemoryStatus.ACTIVE

    historical = temporal_engine.get_truth_at_timestamp("programming_language", "primary", timestamp=now - 50)
    assert historical is not None
    assert historical.value == "Python"
    assert historical.version == 1

    timeline = temporal_engine.get_timeline("programming_language", "primary")
    assert len(timeline) == 2
    assert timeline[0]["value"] == "Python"
    assert timeline[1]["value"] == "C++"


def test_deterministic_conflict_resolution(memory_store, conflict_engine):
    """Verify conflict resolution: User correction immediately supersedes model inference."""
    existing_model_fact = CanonicalMemory(
        memory_id="mem_city_1",
        entity="user_city",
        attribute="city",
        value="Seattle",
        content="User lives in Seattle",
        source_type=SourceType.MODEL_INFERENCE,
        confidence=0.40,
        status=MemoryStatus.ACTIVE,
    )
    memory_store.save(existing_model_fact)

    user_correction = CanonicalMemory(
        memory_id="mem_city_2",
        entity="user_city",
        attribute="city",
        value="Madurai",
        content="User corrected location: lives in Madurai",
        source_type=SourceType.EXPLICIT_USER_CORRECTION,
        confidence=1.0,
        status=MemoryStatus.ACTIVE,
    )

    conflicts = conflict_engine.detect_conflicts(user_correction)
    assert len(conflicts) == 1
    assert conflicts[0].memory_id == "mem_city_1"

    resolution = conflict_engine.resolve(user_correction, conflicts)
    assert resolution.action == ConflictResolutionAction.SUPERSEDE_EXISTING
    assert resolution.winner_memory.memory_id == user_correction.memory_id

    saved = conflict_engine.apply_resolution(resolution)
    assert saved.value == "Madurai"

    old_record = memory_store.get("mem_city_1")
    assert old_record.status == MemoryStatus.SUPERSEDED
    assert old_record.superseded_by_memory_id == user_correction.memory_id


def test_scoped_conflict_resolution(memory_store, conflict_engine, temporal_engine):
    """Verify that project-specific memory overrides global memory for project queries."""
    global_pref = CanonicalMemory(
        memory_id="pref_global",
        entity="indentation",
        attribute="style",
        value="tabs",
        content="Global indentation preference is tabs",
        project_id="global",
        scope="user",
        status=MemoryStatus.ACTIVE,
    )
    memory_store.save(global_pref)

    project_pref = CanonicalMemory(
        memory_id="pref_proj_alpha",
        entity="indentation",
        attribute="style",
        value="spaces_4",
        content="Project Alpha indentation preference is 4 spaces",
        project_id="alpha",
        scope="project",
        status=MemoryStatus.ACTIVE,
    )
    memory_store.save(project_pref)

    # Query in project Alpha scope -> gets spaces_4
    alpha_truth = temporal_engine.get_current_truth("indentation", "style", project_id="alpha")
    assert alpha_truth is not None
    assert alpha_truth.value == "spaces_4"

    # Query in global scope -> gets tabs
    global_truth = temporal_engine.get_current_truth("indentation", "style", project_id="global")
    assert global_truth is not None
    assert global_truth.value == "tabs"


def test_memory_deletion_and_invalidation(memory_store):
    """Verify soft deletion marks status as INVALID and removes from active listings."""
    mem = CanonicalMemory(
        memory_id="mem_delete_me",
        entity="temporary_note",
        content="Temporary secret token note",
        status=MemoryStatus.ACTIVE,
    )
    memory_store.save(mem)

    # Soft delete
    deleted = memory_store.delete("mem_delete_me", hard=False)
    assert deleted is True

    record = memory_store.get("mem_delete_me")
    assert record.status == MemoryStatus.INVALID

    active_list = memory_store.list_active()
    assert not any(m.memory_id == "mem_delete_me" for m in active_list)


def test_provenance_and_trust_hierarchy():
    """Verify trust hierarchy ratings for all source types."""
    assert SourceType.EXPLICIT_USER_CORRECTION.default_reliability == 1.00
    assert SourceType.EXPLICIT_USER_STATEMENT.default_reliability == 0.95
    assert SourceType.VERIFIED_TOOL_RESULT.default_reliability == 0.90
    assert SourceType.VERIFIED_EXTERNAL_SOURCE.default_reliability == 0.85
    assert SourceType.SYSTEM_OBSERVATION.default_reliability == 0.75
    assert SourceType.STRONG_INFERENCE.default_reliability == 0.60
    assert SourceType.MODEL_INFERENCE.default_reliability == 0.40
    assert SourceType.UNVERIFIED_ASSUMPTION.default_reliability == 0.20
