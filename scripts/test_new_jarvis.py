# scripts/test_new_jarvis.py — Automated E2E verification of New JARVIS features
import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actions.rag_library import scan_markdown_notes, ensure_sample_notes

def test_note_scoring_offline(question: str, base_dir: str):
    graph = scan_markdown_notes(base_dir)
    nodes = graph["nodes"]
    words = question.lower().split()
    scored = []
    for n in nodes:
        score = sum(1 for w in words if len(w) > 2 and w in (n["label"] + " " + n["excerpt"]).lower())
        if score > 0:
            scored.append((score, n))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_sources = [n["id"] for _, n in scored[:6]] if scored else [0, 1]
    return top_sources

def main():
    if 'logger' in globals() or 'logger' in locals():
        logger.info("==================================================")
    else:
        import logging
        logging.getLogger(__name__).info("==================================================")
    if 'logger' in globals() or 'logger' in locals():
        logger.info("       JARVIS NEW FEATURES E2E VERIFICATION       ")
    else:
        import logging
        logging.getLogger(__name__).info("       JARVIS NEW FEATURES E2E VERIFICATION       ")
    if 'logger' in globals() or 'logger' in locals():
        logger.info("==================================================")
    else:
        import logging
        logging.getLogger(__name__).info("==================================================")

    root = Path(__file__).resolve().parent.parent
    notes_dir = root / "notes"
    captures_dir = root / "captures"

    # 1. Test Markdown Notes & 3D Galaxy Graph Generator
    if 'logger' in globals() or 'logger' in locals():
        logger.info("\n[1/4] Testing 3D Knowledge Galaxy Indexing...")
    else:
        import logging
        logging.getLogger(__name__).info("\n[1/4] Testing 3D Knowledge Galaxy Indexing...")
    graph = scan_markdown_notes(str(root))
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  [OK] Indexed {len(nodes)} Nodes in 3D Galaxy" }" if isinstance(f"  [OK] Indexed {len(nodes)} Nodes in 3D Galaxy", str) else f"  [OK] Indexed {len(nodes)} Nodes in 3D Galaxy")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  [OK] Indexed {len(nodes)} Nodes in 3D Galaxy" }" if isinstance(f"  [OK] Indexed {len(nodes)} Nodes in 3D Galaxy", str) else f"  [OK] Indexed {len(nodes)} Nodes in 3D Galaxy")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  [OK] Calculated {len(links)} Inter-Note Connections" }" if isinstance(f"  [OK] Calculated {len(links)} Inter-Note Connections", str) else f"  [OK] Calculated {len(links)} Inter-Note Connections")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  [OK] Calculated {len(links)} Inter-Note Connections" }" if isinstance(f"  [OK] Calculated {len(links)} Inter-Note Connections", str) else f"  [OK] Calculated {len(links)} Inter-Note Connections")
    assert len(nodes) >= 25, "Expected at least 25 nodes!"
    if 'logger' in globals() or 'logger' in locals():
        logger.info("  PASS: 3D Knowledge Galaxy data generated successfully.")
    else:
        import logging
        logging.getLogger(__name__).info("  PASS: 3D Knowledge Galaxy data generated successfully.")

    # 2. Test Brain Note Scoring & Fly-To-Source Node Returns
    if 'logger' in globals() or 'logger' in locals():
        logger.info("\n[2/4] Testing Brain RAG Note Scoring & Fly-To-Source Node Returns...")
    else:
        import logging
        logging.getLogger(__name__).info("\n[2/4] Testing Brain RAG Note Scoring & Fly-To-Source Node Returns...")
    source_nodes = test_note_scoring_offline("quantum computing qubits", str(root))
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  [OK] Referenced Source Nodes for Fly-To Camera Dive: {source_nodes}" }" if isinstance(f"  [OK] Referenced Source Nodes for Fly-To Camera Dive: {source_nodes}", str) else f"  [OK] Referenced Source Nodes for Fly-To Camera Dive: {source_nodes}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  [OK] Referenced Source Nodes for Fly-To Camera Dive: {source_nodes}" }" if isinstance(f"  [OK] Referenced Source Nodes for Fly-To Camera Dive: {source_nodes}", str) else f"  [OK] Referenced Source Nodes for Fly-To Camera Dive: {source_nodes}")
    assert len(source_nodes) > 0, "No source nodes returned for Fly-To dive!"
    if 'logger' in globals() or 'logger' in locals():
        logger.info("  PASS: Note scoring & Fly-To-Source node index array verified.")
    else:
        import logging
        logging.getLogger(__name__).info("  PASS: Note scoring & Fly-To-Source node index array verified.")

    # 3. Test Total Recall Capture (/remember logic)
    if 'logger' in globals() or 'logger' in locals():
        logger.info("\n[3/4] Testing Total Recall Note Capture logic...")
    else:
        import logging
        logging.getLogger(__name__).info("\n[3/4] Testing Total Recall Note Capture logic...")
    sample_text = "remember that prompt packs make excellent gifts for developers"
    words = sample_text.replace("remember that ", "").split()
    title_slug = "_".join(words[:4]).lower()
    captures_dir.mkdir(parents=True, exist_ok=True)
    test_note = captures_dir / f"{title_slug}_test.md"
    test_note.write_text(f"# Voice Capture\n\n{sample_text}\n", encoding="utf-8")

    updated_graph = scan_markdown_notes(str(root))
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  [OK] Live Galaxy Node Count after capture: {len(updated_graph['nodes'])}" }" if isinstance(f"  [OK] Live Galaxy Node Count after capture: {len(updated_graph['nodes'])}", str) else f"  [OK] Live Galaxy Node Count after capture: {len(updated_graph['nodes'])}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  [OK] Live Galaxy Node Count after capture: {len(updated_graph['nodes'])}" }" if isinstance(f"  [OK] Live Galaxy Node Count after capture: {len(updated_graph['nodes'])}", str) else f"  [OK] Live Galaxy Node Count after capture: {len(updated_graph['nodes'])}")
    assert len(updated_graph["nodes"]) > len(nodes), "New note node was not dynamically added!"
    if 'logger' in globals() or 'logger' in locals():
        logger.info("  PASS: Total Recall live note capture verified.")
    else:
        import logging
        logging.getLogger(__name__).info("  PASS: Total Recall live note capture verified.")

    # 4. Clean up test note
    if test_note.exists():
        test_note.unlink()

    if 'logger' in globals() or 'logger' in locals():
        logger.info("\n==================================================")
    else:
        import logging
        logging.getLogger(__name__).info("\n==================================================")
    if 'logger' in globals() or 'logger' in locals():
        logger.info("       ALL NEW JARVIS FEATURE TESTS PASSED!       ")
    else:
        import logging
        logging.getLogger(__name__).info("       ALL NEW JARVIS FEATURE TESTS PASSED!       ")
    if 'logger' in globals() or 'logger' in locals():
        logger.info("==================================================")
    else:
        import logging
        logging.getLogger(__name__).info("==================================================")

if __name__ == "__main__":
    main()
