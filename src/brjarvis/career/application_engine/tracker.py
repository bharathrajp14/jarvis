# career/application_engine/tracker.py — Canonical Lifecycle Application Tracker Bridge
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..crm.database import get_career_crm_db
from ..crm.state_machine import ApplicationStateMachine
from ..models import Application, ApplicationRecord, ApplicationStatus, JobPosting, PriorityLevel

logger = logging.getLogger("JARVIS.ApplicationTracker")

_DEFAULT_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "workspace" / "Career" / "applications"


class ApplicationTracker:
    """
    ApplicationTracker Bridge integrating legacy tracker API with the
    24-State Canonical CRM Database and Immutable Event Store.
    """

    _INSTANCE: Optional[ApplicationTracker] = None

    def __init__(self, storage_dir: Optional[Path | str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else _DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.crm_db = get_career_crm_db()

    @classmethod
    def get_instance(cls) -> ApplicationTracker:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def create_application(
        self,
        job: JobPosting,
        status: ApplicationStatus = ApplicationStatus.DISCOVERED,
        package_id: Optional[str] = None,
        notes: Optional[List[str]] = None,
    ) -> Application:
        """Create and persist a new canonical application tracking record."""
        app_id = f"APP-{uuid.uuid4().hex[:6].upper()}"
        now_date_str = time.strftime("%Y-%m-%d")

        app = Application(
            application_id=app_id,
            job_id=job.job_id,
            company=job.company,
            job_title=job.title,
            job_url=job.application_url,
            source=job.source,
            platform=job.platform,
            location=job.location,
            employment_type=job.employment_type,
            salary=job.salary,
            application_package_id=package_id,
            application_status=status,
            date_discovered=now_date_str,
            date_shortlisted=now_date_str if status == ApplicationStatus.SHORTLISTED else None,
            date_prepared=now_date_str if status == ApplicationStatus.PREPARING else None,
            last_updated=time.time(),
            priority=PriorityLevel.MEDIUM,
            notes=notes or [f"Discovered from {job.platform} on {now_date_str}"],
        )

        self.crm_db.save_application(app)
        logger.info("📋 Application created: [%s] for %s — %s (%s)", app.application_id, app.company, app.job_title, status.value)
        return app

    def update_status(
        self,
        application_id: str,
        new_status: ApplicationStatus | str,
        note: str = "",
        confirmation_id: Optional[str] = None,
        confirmation_url: Optional[str] = None,
        follow_up_date: Optional[str] = None,
    ) -> Optional[Application]:
        """Advance application lifecycle status and record audit history."""
        try:
            app = ApplicationStateMachine.transition(
                application_id=application_id,
                target_status=new_status,
                source="ApplicationTracker",
                actor="system",
                evidence=note or f"Status changed to {new_status}",
                note=note,
                confirmation_id=confirmation_id,
                confirmation_url=confirmation_url,
            )
            if follow_up_date:
                app.next_followup = follow_up_date
                self.crm_db.save_application(app)
            return app
        except Exception as exc:
            logger.warning("Tracker status update note for %s: %s", application_id, exc)
            return self.crm_db.get_application(application_id)

    def get_application(self, application_id: str) -> Optional[Application]:
        """Fetch application record by ID."""
        return self.crm_db.get_application(application_id)

    def list_applications(self, status: Optional[ApplicationStatus] = None, limit: int = 200) -> List[Application]:
        """List active and historical applications."""
        return self.crm_db.list_applications(status=status, limit=limit)

    def get_funnel_counts(self) -> Dict[str, int]:
        """Retrieve total application count per status category."""
        return self.crm_db.count_applications_by_status()


def get_instance(storage_dir: Optional[Path | str] = None) -> ApplicationTracker:
    return ApplicationTracker.get_instance()


get_application_tracker = get_instance

