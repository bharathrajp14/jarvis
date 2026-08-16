# career/resume_engine/version_manager.py — Resume Version and Variant Manager
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ResumeSchema, ResumeVersionRecord
from memory.canonical_db import get_canonical_db

logger = logging.getLogger("JARVIS.ResumeVersionManager")

_DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace" / "Career" / "versions"


class ResumeVersionManager:
    """
    Manages version control, variants, and lineage tracking for resumes.
    Ensures that tailored versions never overwrite Master Resumes.
    """

    _INSTANCE: Optional[ResumeVersionManager] = None

    def __init__(self, storage_dir: Optional[Path | str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else _DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "version_index.json"
        self._init_db()

    @classmethod
    def get_instance(cls, storage_dir: Optional[Path | str] = None) -> ResumeVersionManager:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls(storage_dir)
        return cls._INSTANCE

    def _init_db(self) -> None:
        try:
            db = get_canonical_db()
            with db.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS resume_versions (
                        version_id TEXT PRIMARY KEY,
                        resume_id TEXT,
                        title TEXT,
                        template_id TEXT,
                        target_role TEXT,
                        job_id TEXT,
                        ats_score REAL,
                        provider TEXT,
                        data_json TEXT,
                        created_at REAL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.debug(f"Resume version DB init note: {e}")

    def register_version(
        self,
        resume: ResumeSchema,
        provider: str = "native",
        docx_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
        html_path: Optional[str] = None,
        canva_design_id: Optional[str] = None,
        canva_edit_url: Optional[str] = None,
    ) -> ResumeVersionRecord:
        """Register a new immutable resume version record."""
        v_id = f"ver_{uuid.uuid4().hex[:10]}"
        content_bytes = json.dumps(resume.to_dict(), sort_keys=True).encode("utf-8")
        src_hash = hashlib.sha256(content_bytes).hexdigest()

        rec = ResumeVersionRecord(
            version_id=v_id,
            resume_id=resume.resume_id,
            title=resume.title,
            template_id=resume.template_id.value if hasattr(resume.template_id, "value") else str(resume.template_id),
            target_role=resume.target_role,
            job_id=resume.job_id_targeted,
            ats_score=resume.ats_score,
            provider=provider,
            canva_design_id=canva_design_id,
            canva_edit_url=canva_edit_url,
            docx_path=docx_path,
            pdf_path=pdf_path,
            html_path=html_path,
            source_hash=src_hash,
            created_at=time.time(),
        )

        # 1. Save JSON snapshot
        snapshot_file = self.storage_dir / f"{v_id}.json"
        snapshot_file.write_text(json.dumps(resume.to_dict(), indent=2), encoding="utf-8")

        # 2. Save SQLite
        try:
            db = get_canonical_db()
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO resume_versions (version_id, resume_id, title, template_id, target_role, job_id, ats_score, provider, data_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec.version_id,
                        rec.resume_id,
                        rec.title,
                        rec.template_id,
                        rec.target_role,
                        rec.job_id,
                        rec.ats_score,
                        rec.provider,
                        json.dumps(rec.to_dict()),
                        rec.created_at,
                    )
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Error persisting version record to DB: {e}")

        logger.info(f"📌 Resume Version registered: [{v_id}] '{rec.title}' ({rec.provider})")
        return rec

    def list_versions(self, limit: int = 50) -> List[ResumeVersionRecord]:
        """List all historical resume versions."""
        versions = []
        try:
            db = get_canonical_db()
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT data_json FROM resume_versions ORDER BY created_at DESC LIMIT ?", (limit,))
                for row in cursor.fetchall():
                    try:
                        d = json.loads(row["data_json"])
                        versions.append(ResumeVersionRecord(**{k: v for k, v in d.items() if k in ResumeVersionRecord.__dataclass_fields__}))
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Version listing error: {e}")
        return versions

    def get_version(self, version_id: str) -> Optional[ResumeSchema]:
        """Retrieve resume schema for a specific historical version."""
        snapshot_file = self.storage_dir / f"{version_id}.json"
        if snapshot_file.exists():
            try:
                data = json.loads(snapshot_file.read_text(encoding="utf-8"))
                return ResumeSchema.from_dict(data)
            except Exception as e:
                logger.error(f"Error loading resume snapshot: {e}")
        return None


def get_instance(storage_dir: Optional[Path | str] = None) -> ResumeVersionManager:
    return ResumeVersionManager.get_instance(storage_dir)


get_version_manager = get_instance

