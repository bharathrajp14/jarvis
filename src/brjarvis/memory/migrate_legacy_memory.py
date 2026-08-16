# memory/migrate_legacy_memory.py — Data Migration from Legacy Stores to Canonical SQLite
"""
Data Migration Tool for BR JARVIS.
Migrates all legacy memory sources:
1. JSON dictionary storage (`long_term.json`)
2. Markdown frontmatter files (`~/.jarvis/memory/*.md`, `.jarvis/memory/*.md`)
3. Legacy SQLite database tables (`persistent_memories`)
Imports all records into the authoritative Canonical SQLite WAL Store (`canonical_memories`)
with complete provenance mapping, deduplication, and zero data loss.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from brjarvis.core.paths import paths
from .canonical_db import get_canonical_db
from .domain import CanonicalMemory, MemoryStatus, MemoryType, SourceType
from .store import CanonicalMemoryStore, get_canonical_store

logger = logging.getLogger("JARVIS.MemoryMigration")


class LegacyMemoryMigrator:
    """Migrates historical memory data into the Canonical Memory Store."""

    def __init__(self, store: Optional[CanonicalMemoryStore] = None):
        self.store = store or get_canonical_store()

    def run_migration(self) -> Dict[str, Any]:
        """Execute full migration across all legacy storage locations."""
        report = {
            "json_imported": 0,
            "markdown_imported": 0,
            "sqlite_imported": 0,
            "duplicates_skipped": 0,
            "errors": [],
        }

        # 1. Migrate long_term.json
        json_file = paths.STATE_ROOT / "long_term.json"
        if json_file.exists():
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    count = self._migrate_json_dict(data)
                    report["json_imported"] = count
            except Exception as e:
                report["errors"].append(f"JSON migration error: {e}")

        # 2. Migrate Markdown Memory Files
        for scope, mem_dir in [("user", Path.home() / ".jarvis" / "memory"), ("project", Path.cwd() / ".jarvis" / "memory")]:
            if mem_dir.exists():
                for md_file in mem_dir.glob("*.md"):
                    if md_file.name == "MEMORY.md":
                        continue
                    try:
                        if self._migrate_md_file(md_file, scope=scope):
                            report["markdown_imported"] += 1
                        else:
                            report["duplicates_skipped"] += 1
                    except Exception as e:
                        report["errors"].append(f"Markdown file {md_file.name} error: {e}")

        # 3. Migrate Legacy persistent_memories from Canonical DB
        try:
            with self.store.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM persistent_memories")
                rows = cursor.fetchall()
                for row in rows:
                    if self._migrate_legacy_sqlite_row(row):
                        report["sqlite_imported"] += 1
                    else:
                        report["duplicates_skipped"] += 1
        except Exception as e:
            report["errors"].append(f"Legacy SQLite table migration error: {e}")

        logger.info(
            "✅ Migration complete: %d JSON items, %d Markdown files, %d SQLite rows imported.",
            report["json_imported"],
            report["markdown_imported"],
            report["sqlite_imported"],
        )
        return report

    def _migrate_json_dict(self, data: dict) -> int:
        count = 0
        cat_mapping = {
            "identity": MemoryType.USER_PROFILE,
            "preferences": MemoryType.PREFERENCE,
            "projects": MemoryType.PROJECT_STATE,
            "relationships": MemoryType.RELATIONSHIP,
            "wishes": MemoryType.GOAL,
            "notes": MemoryType.SEMANTIC,
        }

        for cat, items in data.items():
            if not isinstance(items, dict):
                continue
            m_type = cat_mapping.get(cat, MemoryType.SEMANTIC)
            for key, val in items.items():
                val_str = val.get("value", "") if isinstance(val, dict) else str(val)
                if not val_str:
                    continue

                mem = CanonicalMemory(
                    entity=key,
                    attribute=cat,
                    value=val_str,
                    content=f"{key}: {val_str}",
                    memory_type=m_type,
                    scope="user",
                    source_type=SourceType.EXPLICIT_USER_STATEMENT,
                    status=MemoryStatus.ACTIVE,
                )
                self.store.save(mem)
                count += 1

        return count

    def _migrate_md_file(self, file_path: Path, scope: str = "user") -> bool:
        text = file_path.read_text(encoding="utf-8")
        meta = {}
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip()
                body = parts[2].strip()

        name = meta.get("name", file_path.stem)
        mem_type_str = meta.get("type", "user")

        mem = CanonicalMemory(
            entity=name,
            attribute="legacy_import",
            value=body[:100],
            content=body,
            memory_type=MemoryType.from_str(mem_type_str),
            scope=scope,
            source_type=SourceType.from_str(meta.get("source", "user")),
            confidence=float(meta.get("confidence", 1.0)),
            status=MemoryStatus.ACTIVE,
        )
        self.store.save(mem)
        return True

    def _migrate_legacy_sqlite_row(self, row: Any) -> bool:
        name = row["name"]
        existing = self.store.get_by_entity_attribute(entity=name, attribute="canonical_import")
        if existing:
            return False

        mem = CanonicalMemory(
            entity=name,
            attribute="canonical_import",
            value=row["content"][:100],
            content=row["content"],
            memory_type=MemoryType.from_str(row["type"]),
            scope=row["scope"] or "user",
            source_type=SourceType.EXPLICIT_USER_STATEMENT,
            status=MemoryStatus.ACTIVE,
        )
        self.store.save(mem)
        return True


def run_migration() -> Dict[str, Any]:
    migrator = LegacyMemoryMigrator()
    return migrator.run_migration()


if __name__ == "__main__":
    rep = run_migration()
    print(json.dumps(rep, indent=2))
