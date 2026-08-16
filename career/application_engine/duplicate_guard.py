# career/application_engine/duplicate_guard.py — Duplicate Application Protection
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Tuple

from career.models import ApplicationRecord, JobPosting

logger = logging.getLogger("JARVIS.DuplicateGuard")


class DuplicateApplicationGuard:
    """
    Prevents accidental duplicate applications to the same job or company within a protective cooldown window.
    """

    COOLDOWN_DAYS = 90

    @classmethod
    def check_duplicate(
        cls,
        job: JobPosting,
        applications: List[ApplicationRecord],
        cooldown_days: int = COOLDOWN_DAYS,
    ) -> Tuple[bool, str, Optional[ApplicationRecord]]:
        """
        Check if the candidate has already applied to this job or recently to this role at the same company.
        """
        now = time.time()
        cooldown_seconds = cooldown_days * 86400

        for app in applications:
            # 1. Exact job_id match
            if app.job_id == job.job_id:
                return (
                    True,
                    f"Already applied to job ID '{job.job_id}' on {time.ctime(app.applied_at or app.last_status_change)} (Status: {app.status}).",
                    app,
                )

            # 2. Same company & role title within cooldown
            time_diff = now - app.last_status_change
            if (
                app.company.lower() == job.company.lower()
                and app.role_title.lower() == job.title.lower()
                and time_diff < cooldown_seconds
            ):
                days_ago = int(time_diff / 86400)
                return (
                    True,
                    f"Already applied for '{job.title}' at {job.company} {days_ago} days ago (Status: {app.status}).",
                    app,
                )

        return False, "No prior conflicting applications found.", None
