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

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.debug('Suppressed exception: %s', e)
        else:
            import logging
            logging.getLogger(__name__).debug('Suppressed exception: %s', e)
# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def migrate(dry_run: bool = False):
    from memory.persistent_store import (
        load_entries, _sync_to_vector, _get_chroma_collection, _chroma_available,
        USER_MEMORY_DIR
    )

    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 55 }" if isinstance("=" * 55, str) else "=" * 55)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 55 }" if isinstance("=" * 55, str) else "=" * 55)
    if 'logger' in globals() or 'logger' in locals():
        logger.info("  JARVIS MK37 — Memory Migration to ChromaDB")
    else:
        import logging
        logging.getLogger(__name__).info("  JARVIS MK37 — Memory Migration to ChromaDB")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 55 }" if isinstance("=" * 55, str) else "=" * 55)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 55 }" if isinstance("=" * 55, str) else "=" * 55)

    if not _chroma_available:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning("\n[ERROR] ChromaDB is not installed.")
        else:
            import logging
            logging.getLogger(__name__).warning("\n[ERROR] ChromaDB is not installed.")
        if 'logger' in globals() or 'logger' in locals():
            logger.info("        Run: pip install chromadb")
        else:
            import logging
            logging.getLogger(__name__).info("        Run: pip install chromadb")
        if 'logger' in globals() or 'logger' in locals():
            logger.info("        The system will continue using keyword search until installed.")
        else:
            import logging
            logging.getLogger(__name__).info("        The system will continue using keyword search until installed.")
        return

    # Load all existing entries
    user_entries = load_entries("user")
    project_entries = load_entries("project")
    all_entries = user_entries + project_entries

    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"\n  Found {len(user_entries)} user memories" }" if isinstance(f"\n  Found {len(user_entries)} user memories", str) else f"\n  Found {len(user_entries)} user memories")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"\n  Found {len(user_entries)} user memories" }" if isinstance(f"\n  Found {len(user_entries)} user memories", str) else f"\n  Found {len(user_entries)} user memories")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  Found {len(project_entries)} project memories" }" if isinstance(f"  Found {len(project_entries)} project memories", str) else f"  Found {len(project_entries)} project memories")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  Found {len(project_entries)} project memories" }" if isinstance(f"  Found {len(project_entries)} project memories", str) else f"  Found {len(project_entries)} project memories")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  Total: {len(all_entries)}" }" if isinstance(f"  Total: {len(all_entries)}", str) else f"  Total: {len(all_entries)}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  Total: {len(all_entries)}" }" if isinstance(f"  Total: {len(all_entries)}", str) else f"  Total: {len(all_entries)}")

    if not all_entries:
        if 'logger' in globals() or 'logger' in locals():
            logger.info("\n  No memories to migrate.")
        else:
            import logging
            logging.getLogger(__name__).info("\n  No memories to migrate.")
        return

    if dry_run:
        if 'logger' in globals() or 'logger' in locals():
            logger.info("\n  [DRY RUN] Would index the following memories:")
        else:
            import logging
            logging.getLogger(__name__).info("\n  [DRY RUN] Would index the following memories:")
        for e in all_entries:
            if 'logger' in globals() or 'logger' in locals():
                logger.info(f"{ f"    - [{e.type}] {e.name}: {e.description[:60]}" }" if isinstance(f"    - [{e.type}] {e.name}: {e.description[:60]}", str) else f"    - [{e.type}] {e.name}: {e.description[:60]}")
            else:
                import logging
                logging.getLogger(__name__).info(f"{ f"    - [{e.type}] {e.name}: {e.description[:60]}" }" if isinstance(f"    - [{e.type}] {e.name}: {e.description[:60]}", str) else f"    - [{e.type}] {e.name}: {e.description[:60]}")
        if 'logger' in globals() or 'logger' in locals():
            logger.info("\n  Run without --dry-run to execute.")
        else:
            import logging
            logging.getLogger(__name__).info("\n  Run without --dry-run to execute.")
        return

    # Index into ChromaDB
    coll = _get_chroma_collection()
    if coll is None:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning("\n[ERROR] Could not create ChromaDB collection.")
        else:
            import logging
            logging.getLogger(__name__).warning("\n[ERROR] Could not create ChromaDB collection.")
        return

    indexed = 0
    for entry in all_entries:
        try:
            _sync_to_vector(entry)
            indexed += 1
            if 'logger' in globals() or 'logger' in locals():
                logger.info(f"{ f"  ✓ {entry.name}" }" if isinstance(f"  ✓ {entry.name}", str) else f"  ✓ {entry.name}")
            else:
                import logging
                logging.getLogger(__name__).info(f"{ f"  ✓ {entry.name}" }" if isinstance(f"  ✓ {entry.name}", str) else f"  ✓ {entry.name}")
        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.debug('Suppressed exception: %s', e)
            else:
                import logging
                logging.getLogger(__name__).debug('Suppressed exception: %s', e)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"\n  Indexed: {indexed}/{len(all_entries)} memories" }" if isinstance(f"\n  Indexed: {indexed}/{len(all_entries)} memories", str) else f"\n  Indexed: {indexed}/{len(all_entries)} memories")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"\n  Indexed: {indexed}/{len(all_entries)} memories" }" if isinstance(f"\n  Indexed: {indexed}/{len(all_entries)} memories", str) else f"\n  Indexed: {indexed}/{len(all_entries)} memories")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}" }" if isinstance(f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}", str) else f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}" }" if isinstance(f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}", str) else f"  ChromaDB path: {USER_MEMORY_DIR / '.chromadb'}")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"\n  Migration complete. Vector search is now active." }" if isinstance(f"\n  Migration complete. Vector search is now active.", str) else f"\n  Migration complete. Vector search is now active.")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"\n  Migration complete. Vector search is now active." }" if isinstance(f"\n  Migration complete. Vector search is now active.", str) else f"\n  Migration complete. Vector search is now active.")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only." }" if isinstance(f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only.", str) else f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only.")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only." }" if isinstance(f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only.", str) else f"\n  Rollback: delete {USER_MEMORY_DIR / '.chromadb'} to revert to keyword-only.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    migrate(dry_run=dry)
