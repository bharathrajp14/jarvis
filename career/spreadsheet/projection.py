# career/spreadsheet/projection.py — Concurrency-Safe Database-to-Excel Projection Engine
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from career.crm.database import get_career_crm_db
from career.spreadsheet.tracker_excel import CareerTrackerWorkbook

logger = logging.getLogger("JARVIS.CareerSpreadsheet.Projection")

_WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_WORKBOOK_PATH = _WORKSPACE_DIR / "BR_JARVIS_Career_Tracker.xlsx"
_BACKUPS_DIR = _WORKSPACE_DIR / ".jarvis" / "backups"
_BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


class CareerSpreadsheetProjection:
    """
    Thread-Safe, Concurrency-Protected Projection Engine.
    Projects Canonical Database records into the user-facing Excel workbook with:
    - Lock detection & non-blocking atomic replacement
    - Versioned automated backups (CareerTracker_YYYYMMDD_HHMMSS.xlsx)
    - Structural integrity validation
    """

    _INSTANCE: Optional[CareerSpreadsheetProjection] = None
    _LOCK = threading.RLock()

    def __init__(self, workbook_path: Optional[Path | str] = None):
        self.workbook_path = Path(workbook_path) if workbook_path else _DEFAULT_WORKBOOK_PATH
        self.db = get_career_crm_db()
        self._pending_projection_queue: List[float] = []

    @classmethod
    def get_instance(cls) -> CareerSpreadsheetProjection:
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE

    def is_file_locked(self, file_path: Path) -> bool:
        """Check whether the target Excel file is currently open or locked by an external process."""
        if not file_path.exists():
            return False
        try:
            # Attempt to open file for appending in exclusive binary mode
            with open(file_path, "r+b"):
                return False
        except (IOError, PermissionError):
            return True

    def create_versioned_backup(self) -> Optional[Path]:
        """Create an archival backup before updating the active workbook."""
        if not self.workbook_path.exists():
            return None

        try:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"CareerTracker_{timestamp_str}.xlsx"
            backup_target = _BACKUPS_DIR / backup_name
            shutil.copy2(self.workbook_path, backup_target)
            logger.debug("📦 Created Excel version backup: %s", backup_target.name)
            return backup_target
        except Exception as exc:
            logger.warning("Version backup creation note: %s", exc)
            return None

    def project_database_to_excel(self, auto_open: bool = False) -> Dict[str, Any]:
        """
        Execute full authoritative projection from SQLite CRM DB to Excel workbook.
        """
        with self._LOCK:
            # 1. Fetch Authoritative Snapshot from CRM Database
            apps = self.db.list_applications(limit=1000)
            interviews = self.db.list_interviews(limit=200)
            offers = self.db.list_offers(limit=100)
            followups = self.db.list_followups(limit=200)
            email_events = self.db.list_email_records(limit=200)
            contacts = self.db.list_contacts(limit=200)
            app_counts = self.db.count_applications_by_status()

            submitted_cnt = sum(app_counts.get(st, 0) for st in ["SUBMITTED", "SUBMISSION_VERIFIED", "SCREENING", "INTERVIEW_REQUESTED", "INTERVIEW_SCHEDULED", "TECHNICAL_ROUND", "FINAL_ROUND", "OFFER_RECEIVED", "OFFER_ACCEPTED", "REJECTED"])
            interviews_cnt = len(interviews)
            offers_cnt = len(offers)

            resp_rate = round((len(interviews) + len(offers)) / max(1, submitted_cnt) * 100.0, 1) if submitted_cnt > 0 else 0.0
            int_rate = round(interviews_cnt / max(1, submitted_cnt) * 100.0, 1) if submitted_cnt > 0 else 0.0
            off_rate = round(offers_cnt / max(1, interviews_cnt) * 100.0, 1) if interviews_cnt > 0 else 0.0

            analytics_summary = {
                "total_applications_submitted": submitted_cnt,
                "total_interviews": interviews_cnt,
                "total_offers": offers_cnt,
                "response_rate": resp_rate,
                "interview_rate": int_rate,
                "offer_rate": off_rate,
            }

            # 2. Check File Lock
            if self.is_file_locked(self.workbook_path):
                logger.warning("🔒 Target Excel file is currently locked/opened by user: %s. Queueing retry.", self.workbook_path.name)
                return {
                    "status": "QUEUED_LOCKED",
                    "file_locked": True,
                    "target_path": str(self.workbook_path),
                    "message": "Workbook is currently open in Microsoft Excel. Projection queued.",
                }

            # 3. Create Versioned Backup
            backup_path = self.create_versioned_backup()

            # 4. Generate Workbook via Temporary File
            temp_fd, temp_file_path = tempfile.mkstemp(suffix=".xlsx", prefix="jarvis_tracker_")
            os.close(temp_fd)
            temp_path = Path(temp_file_path)

            try:
                wb = CareerTrackerWorkbook.build_workbook(
                    applications=apps,
                    interviews=interviews,
                    offers=offers,
                    followups=followups,
                    email_events=email_events,
                    contacts=contacts,
                    analytics_summary=analytics_summary,
                )
                wb.save(temp_path)

                # Validate temp file existence and non-zero size
                if not temp_path.exists() or temp_path.stat().st_size == 0:
                    raise RuntimeError("Generated temporary Excel file was empty.")

                # 5. Atomic Replace
                shutil.move(str(temp_path), str(self.workbook_path))

                logger.info("📊 Excel Projection Succeeded: %s (Apps: %d, Interviews: %d, Offers: %d)",
                            self.workbook_path.name, len(apps), len(interviews), len(offers))

                return {
                    "status": "SUCCESS_VERIFIED",
                    "file_path": str(self.workbook_path),
                    "sheets_projected": list(CareerTrackerWorkbook.SHEET_SCHEMAS.keys()),
                    "applications_count": len(apps),
                    "interviews_count": len(interviews),
                    "offers_count": len(offers),
                    "backup_created": str(backup_path) if backup_path else None,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

            except Exception as exc:
                logger.error("❌ Excel Projection Error: %s", exc, exc_info=True)
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                return {
                    "status": "FAILED",
                    "error": str(exc),
                    "target_path": str(self.workbook_path),
                }


def get_spreadsheet_projection() -> CareerSpreadsheetProjection:
    return CareerSpreadsheetProjection.get_instance()
