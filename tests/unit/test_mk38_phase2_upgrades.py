# tests/test_mk38_phase2_upgrades.py — Unit & Integration Tests for MK38 Phase 8.2 Upgrades
import pytest
import tempfile
import time
from pathlib import Path

from memory.temporal_kg import TemporalKnowledgeGraph, TemporalEdge
from core.code_graph import WorkspaceCodeGraph, SymbolDefinition


def test_temporal_knowledge_graph():
    with tempfile.TemporaryDirectory() as tmpdir:
        kg = TemporalKnowledgeGraph(db_dir=Path(tmpdir))

        t0 = time.time()
        # Add initial relationship
        e1 = kg.add_temporal_relation("Workspace-01", "uses_backend", "Gemini-3.5", valid_from=t0)
        assert e1.source_id == "Workspace-01"
        assert e1.target_id == "Gemini-3.5"

        t1 = t0 + 5.0
        # Mutation: change backend
        e2 = kg.add_temporal_relation("Workspace-01", "uses_backend", "Gemini-3.6", valid_from=t1)
        assert e2.target_id == "Gemini-3.6"

        # Query snapshot at t0 + 2.0 (should return Gemini-3.5)
        snap_t0 = kg.query_as_of(t0 + 2.0)
        assert len(snap_t0) == 1
        assert snap_t0[0].target_id == "Gemini-3.5"

        # Query snapshot at t1 + 2.0 (should return Gemini-3.6)
        snap_t1 = kg.query_as_of(t1 + 2.0)
        assert len(snap_t1) == 1
        assert snap_t1[0].target_id == "Gemini-3.6"

        # Entity history
        hist = kg.get_entity_history("Workspace-01")
        assert len(hist) == 2


def test_workspace_code_graph():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / "sample_module.py"
        tmp_file.write_text(
            'class SampleClass:\n'
            '    """Sample docstring."""\n'
            '    def sample_method(self):\n'
            '        pass\n\n'
            'def sample_function():\n'
            '    return 42\n',
            encoding="utf-8",
        )

        cg = WorkspaceCodeGraph()
        cg.index_file(tmp_file)

        # Definition lookups
        cls_defs = cg.find_definition("SampleClass")
        assert len(cls_defs) == 1
        assert cls_defs[0].symbol_type == "class"
        assert cls_defs[0].docstring == "Sample docstring."

        fn_defs = cg.find_definition("sample_function")
        assert len(fn_defs) == 1
        assert fn_defs[0].symbol_type == "function"

        # Reference lookups
        refs = cg.find_references("sample_function")
        assert len(refs) >= 1
        assert refs[0]["line_number"] == 6
