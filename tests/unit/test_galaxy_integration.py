# tests/test_galaxy_integration.py — Unit & Integration tests for 3D Knowledge Galaxy
import pytest
from pathlib import Path
import shutil
from actions.rag_library import scan_markdown_notes, galaxy_chat, ensure_sample_notes

def test_ensure_sample_notes(tmp_path):
    notes_dir = tmp_path / "notes"
    ensure_sample_notes(notes_dir)
    md_files = list(notes_dir.glob("*.md"))
    assert len(md_files) == 25, f"Expected 25 sample notes, got {len(md_files)}"

def test_scan_markdown_notes(tmp_path):
    notes_dir = tmp_path / "notes"
    captures_dir = tmp_path / "captures"
    notes_dir.mkdir(parents=True)
    captures_dir.mkdir(parents=True)

    (notes_dir / "note_one.md").write_text("# Note One\n\nMentions [[Note Two]] for quantum calculations.", encoding="utf-8")
    (notes_dir / "note_two.md").write_text("# Note Two\n\nQuantum algorithms and core logic.", encoding="utf-8")

    data = scan_markdown_notes(str(tmp_path))
    assert "nodes" in data and "links" in data
    assert len(data["nodes"]) == 2
    assert any(link["source"] == 0 and link["target"] == 1 for link in data["links"])

def test_galaxy_chat(tmp_path):
    notes_dir = tmp_path / "notes"
    ensure_sample_notes(notes_dir)
    res = galaxy_chat("What is quantum computing?", base_dir=str(tmp_path))
    assert "answer" in res
    assert "nodes" in res
    assert isinstance(res["nodes"], list)
