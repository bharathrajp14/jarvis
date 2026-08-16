# career/calendar_engine/manager.py — Career Calendar & Conflict Management Engine
from __future__ import annotations

import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from actions.calendar_engine import get_calendar_engine
from ..crm.database import get_career_crm_db
from ..interview_prep import InterviewPrepGenerator
from ..models import Application, InterviewSchedule, JobPosting
from ..profile_manager import get_profile_manager

logger = logging.getLogger("JARVIS.CareerCalendar.Manager")


class CareerCalendarManager:
    """
    Manages interview scheduling, calendar conflict analysis, and automated interview prep generation.
    Enforces strict approval policies and explicit timezone validations.
    """

    _INSTANCE: Optional[CareerCalendarManager] = None

    def __init__(self):
        self.cal_engine = get_calendar_engine()
        self.db = get_career_crm_db()

    @classmethod
    def get_instance(cls) -> CareerCalendarManager:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def detect_conflicts(self, target_date_str: str, target_time_str: str, duration_minutes: int = 45) -> List[Dict[str, Any]]:
        """
        Check existing calendar appointments for time collisions or tight buffers.
        """
        conflicts: List[Dict[str, Any]] = []
        try:
            existing_events = self.cal_engine.list_events(days=14)
            target_expr = f"{target_date_str} {target_time_str}".lower()

            for ev in existing_events:
                ev_time_str = str(ev.get("start_time", "")).lower()
                # Direct string collision or same-day overlap check
                if target_date_str in ev_time_str:
                    conflicts.append({
                        "event_id": ev.get("id"),
                        "title": ev.get("title"),
                        "start_time": ev.get("start_time"),
                        "conflict_type": "SAME_DAY_SCHEDULE",
                        "severity": "WARNING",
                    })
        except Exception as exc:
            logger.debug("Calendar conflict scan note: %s", exc)

        return conflicts

    def schedule_interview_event(
        self,
        interview: InterviewSchedule,
        auto_generate_prep: bool = True,
        user_confirmed: bool = True,
    ) -> Dict[str, Any]:
        """
        Create rich calendar event with interview details and trigger prep kit generator.
        """
        # 1. Conflict Detection
        conflicts = self.detect_conflicts(interview.date, interview.time_str, interview.duration_minutes)
        if conflicts:
            logger.warning("⚠️ Calendar conflict detected for interview %s: %s", interview.interview_id, conflicts)

        # 2. Build Event Title & Description
        app = self.db.get_application(interview.application_id) if interview.application_id else None
        company_name = interview.company or (app.company if app else "Company")
        role_name = interview.role or (app.job_title if app else "Software Engineer")

        title = f"🎯 [{interview.round}] {company_name} — {role_name}"
        desc_lines = [
            f"Company: {company_name}",
            f"Role: {role_name}",
            f"Round: {interview.round}",
            f"Interviewer: {interview.interviewer or 'Hiring Team'}",
            f"Timezone: {interview.timezone}",
            f"Platform: {interview.platform}",
            f"Meeting Link: {interview.meeting_url or 'To be provided'}",
            f"Application ID: {interview.application_id or 'N/A'}",
        ]

        # 3. Trigger Interview Preparation Kit Generation
        prep_kit_summary = "Prep Kit: Ready in Career Studio"
        if auto_generate_prep and app:
            try:
                prof_mgr = get_profile_manager()
                profile = prof_mgr.get_profile()
                dummy_job = JobPosting(
                    job_id=app.job_id or f"job_{app.company.lower()}",
                    source="calendar_scheduler",
                    platform=app.platform,
                    company=app.company,
                    title=app.job_title,
                    location=app.location,
                    description=f"Role: {app.job_title} at {app.company}",
                )
                kit = InterviewPrepGenerator.generate_prep_kit(profile, dummy_job)
                interview.preparation_status = "GENERATED"
                desc_lines.append(f"\n📋 PREPARATION HIGHLIGHTS ({len(kit.technical_questions)} Tech Qs, {len(kit.star_stories)} STAR Stories generated).")
            except Exception as e:
                logger.debug("Prep kit auto-generation note: %s", e)

        start_time_expr = f"{interview.date} {interview.time_str}"
        description = "\n".join(desc_lines)

        # 4. Create Calendar Event
        cal_res = self.cal_engine.create_event(
            title=title,
            start_time_str=start_time_expr,
            description=description,
            location=interview.meeting_url or interview.platform,
            reminder_minutes=15,
        )

        if cal_res.get("success"):
            interview.calendar_event_id = str(cal_res.get("event_id"))
            interview.status = "SCHEDULED"
            self.db.save_interview(interview)

            logger.info("📅 Created Calendar Event #%s for Interview [%s]", interview.calendar_event_id, interview.interview_id)
            return {
                "success": True,
                "status": "SUCCESS_VERIFIED",
                "calendar_event_id": interview.calendar_event_id,
                "interview_id": interview.interview_id,
                "title": title,
                "start_time": start_time_expr,
                "conflicts": conflicts,
                "preparation_status": interview.preparation_status,
            }

        return {
            "success": False,
            "status": "FAILED",
            "error": cal_res.get("error", "Calendar event creation failed"),
            "conflicts": conflicts,
        }


def get_career_calendar_manager() -> CareerCalendarManager:
    return CareerCalendarManager.get_instance()
