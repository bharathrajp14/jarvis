# career/crm/followup_engine.py — Policy-Driven Follow-Up Scheduler & Draft Generator
from __future__ import annotations

import datetime
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .database import get_career_crm_db
from ..models import Application, ApplicationStatus, FollowupRecord, PriorityLevel

logger = logging.getLogger("JARVIS.CareerCRM.FollowupEngine")


class FollowupEngine:
    """
    Automated Follow-up Lifecycle Engine.
    Calculates milestone follow-up dates and generates professional follow-up email drafts in DRAFT_ONLY state.
    """

    _INSTANCE: Optional[FollowupEngine] = None

    def __init__(self):
        self.db = get_career_crm_db()

    @classmethod
    def get_instance(cls) -> FollowupEngine:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def schedule_initial_followup(
        self,
        application: Application,
        days_delay: int = 6,
        reason: str = "First follow-up after application submission"
    ) -> FollowupRecord:
        """Schedule initial follow-up task when application is submitted."""
        due_date = (datetime.date.today() + datetime.timedelta(days=days_delay)).strftime("%Y-%m-%d")
        
        # Update application's next_followup date
        application.next_followup = due_date
        self.db.save_application(application)

        record = FollowupRecord(
            followup_id=f"FOL-{uuid.uuid4().hex[:6].upper()}",
            application_id=application.application_id,
            company=application.company,
            role=application.job_title,
            reason=reason,
            due_date=due_date,
            priority=application.priority,
            status="PENDING",
            notes=[f"Scheduled automatically on {datetime.date.today().strftime('%Y-%m-%d')} for {due_date} (+{days_delay}d)"]
        )

        self.db.save_followup(record)
        logger.info("⏰ Scheduled follow-up #%s for [%s] %s (Due: %s)", record.followup_id, application.application_id, application.company, due_date)
        return record

    def schedule_followups_for_application(self, application_id: str) -> List[FollowupRecord]:
        """Schedule full milestone follow-up plan (Day 6 & Day 13) for an application."""
        app = self.db.get_application(application_id)
        if not app:
            raise ValueError(f"Application ID '{application_id}' not found.")
        f1 = self.schedule_initial_followup(app, days_delay=6)
        f2 = self.schedule_second_followup(app, days_delay=13)
        return [f1, f2]


    def schedule_second_followup(
        self,
        application: Application,
        days_delay: int = 7,
        reason: str = "Second follow-up (2 weeks post-submission check-in)"
    ) -> FollowupRecord:
        """Schedule second follow-up if no recruiter response."""
        due_date = (datetime.date.today() + datetime.timedelta(days=days_delay)).strftime("%Y-%m-%d")
        application.next_followup = due_date
        self.db.save_application(application)

        record = FollowupRecord(
            followup_id=f"FOL-{uuid.uuid4().hex[:6].upper()}",
            application_id=application.application_id,
            company=application.company,
            role=application.job_title,
            reason=reason,
            due_date=due_date,
            priority=PriorityLevel.HIGH,
            status="PENDING",
            notes=[f"Scheduled second follow-up on {datetime.date.today().strftime('%Y-%m-%d')} for {due_date}"]
        )

        self.db.save_followup(record)
        return record

    def generate_followup_draft(
        self,
        followup_id: str,
        candidate_name: str = "Bharath",
        recruiter_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a concise, professional follow-up email draft.
        Never auto-sends; strictly marked DRAFT_ONLY for user approval.
        """
        followups = self.db.list_followups()
        target = next((f for f in followups if f.followup_id == followup_id), None)
        if not target:
            raise ValueError(f"Follow-up ID '{followup_id}' not found.")

        app = self.db.get_application(target.application_id)
        applied_date_str = app.date_applied if app and app.date_applied else "recently"
        recipient_greeting = f"Dear {recruiter_name.strip()}," if recruiter_name else "Dear Hiring Team,"

        subject = f"Following up on Application: {target.role} — {candidate_name}"
        body = f"""{recipient_greeting}

I hope this message finds you well.

I am writing to politely follow up on my application for the {target.role} position at {target.company}, submitted on {applied_date_str}.

I remain very interested in the opportunity to contribute to {target.company}'s engineering objectives and would welcome any updates on the selection process or any additional details you might need from my end.

Thank you for your time and consideration.

Best regards,
{candidate_name}"""

        target.draft_subject = subject
        target.draft_body = body
        target.status = "DRAFT_GENERATED"
        target.notes.append(f"Follow-up draft generated on {time.strftime('%Y-%m-%d %H:%M')}")
        self.db.save_followup(target)

        return {
            "followup_id": target.followup_id,
            "application_id": target.application_id,
            "company": target.company,
            "role": target.role,
            "status": "DRAFT_ONLY",
            "subject": subject,
            "body": body,
            "due_date": target.due_date,
            "requires_approval": True,
        }

    def complete_followup(self, followup_id: str, note: Optional[str] = None) -> FollowupRecord:
        """Mark a follow-up action as completed."""
        followups = self.db.list_followups()
        target = next((f for f in followups if f.followup_id == followup_id), None)
        if not target:
            raise ValueError(f"Follow-up ID '{followup_id}' not found.")

        now_str = time.strftime("%Y-%m-%d")
        target.status = "COMPLETED"
        target.completed_date = now_str
        if note:
            target.notes.append(f"Completed on {now_str}: {note}")

        self.db.save_followup(target)
        return target

    def get_pending_followups(self, due_within_days: int = 3) -> List[FollowupRecord]:
        """Fetch pending follow-ups that are due or overdue."""
        all_pending = self.db.list_followups(status="PENDING") + self.db.list_followups(status="DRAFT_GENERATED")
        cutoff = (datetime.date.today() + datetime.timedelta(days=due_within_days)).strftime("%Y-%m-%d")
        
        due_items = [f for f in all_pending if f.due_date <= cutoff]
        return due_items


def get_followup_engine() -> FollowupEngine:
    return FollowupEngine.get_instance()
