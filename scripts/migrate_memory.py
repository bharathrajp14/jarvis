# scripts/migrate_memory.py
"""
Migration script: seed ChromaDB vector store from existing JSON/file memory.

Reads all .md memory files from ~/.jarvis/memory/ and indexes them into
the ChromaDB persistent store for semantic similarity search.

Usage:
    python scripts/migrate_memory.py
    python scripts/migrate_memory.py --dry-run    # preview only

Rollback:
    Delete ~/.jarvis/memory/.chromadb/ directory to revert to keyword-only search.
    The JSON/file store is never modified — this is purely additive.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def migrate(dry_run: bool = False):
    from memory.persistent_store import (
        load_entries, _sync_to_vector, _get_chroma_collection, _chroma_available,
        USER_MEMORY_DIR
    )

    logger.info("=" * 55)
    logger.info("  JARVIS MK37 — Memory Migration to ChromaDB")
    logger.info("=" * 55)

    if not _chroma_available:
        logger.warning("\n[ERROR] ChromaDB is not installed.")
        logger.info("        Run: pip install chromadb")
        logger.info("        The system will continue using keyword search until installed.")
        return

    # Load all existing entries
    user_entries = load_entries("user")
    project_entries = load_entries("project")
    all_entries = user_entries + project_entries

    logger.info(f"\n  Found {len(user_entries)} user memories")
    logger.info(f"  Found {len(project_entries)} project memories")
    logger.info(f"  Total: {len(all_entries)}")

    if not all_entries:
        logger.info("\n  No memories to migrate.")
        return

    if dry_run:
        logger.info("\n  [DRY RUN] Would index the following memories:")
        for e in all_entries:
            logger.info(f"    - [{e.type}] {e.name}: {e.description[:60]}")
        logger.info("\n  Run without --dry-run to execute.")
        return

    # Index into ChromaDB
    coll = _get_chroma_collection()
    if coll is None:
        logger.warning("\n[ERROR] Could not create ChromaDB collection.")
        return

    indexed = 0
    for entry in all_entries:
        try:
            _sync_to_vector(entry)
            indexed += 1
            logger.info(f"  ✓ {entry.name}")
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    logger.info(f"\n  Indexed: {indexed}/{len(all_entries)} memories")
    logger.info(f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}")
    logger.info(f"\n  Migration complete. Vector search is now active.")
    logger.info(f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    migrate(dry_run=dry)
