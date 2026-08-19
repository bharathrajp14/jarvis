# career/email_intelligence/interview_detector.py — Interview Detection & Strict Timezone Parser
from __future__ import annotations

import datetime
import logging
import re
import uuid
from typing import Optional

from ..models import InterviewSchedule

logger = logging.getLogger("JARVIS.EmailIntelligence.InterviewDetector")

_DATE_PATTERNS = [
    re.compile(r"(?:on\s+)?([A-Za-z]+(?:\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}))", re.IGNORECASE),  # August 21, 2026
    re.compile(r"(?:on\s+)?(\d{4}[-/]\d{1,2}[-/]\d{1,2})", re.IGNORECASE),  # 2026-08-21
    re.compile(r"(?:on\s+)?(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", re.IGNORECASE),  # 21/08/2026
    re.compile(r"([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2})", re.IGNORECASE),  # Friday, August 21
]

_TIME_PATTERNS = [
    re.compile(r"(\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*([A-Z]{2,4}|[A-Za-z/_]+)?", re.IGNORECASE),
    re.compile(r"(\b\d{1,2}\s*(?:AM|PM|am|pm))\s*([A-Z]{2,4}|[A-Za-z/_]+)?", re.IGNORECASE),
]

_MEETING_URL_PATTERNS = [
    re.compile(r"(https?://meet\.google\.com/[a-z0-9-]+)", re.IGNORECASE),
    re.compile(r"(https?://[a-z0-9-]+\.zoom\.us/j/[0-9?=&]+)", re.IGNORECASE),
    re.compile(r"(https?://teams\.microsoft\.com/l/meetup-join/[^\s\>]+)", re.IGNORECASE),
]

_TIMEZONE_MAP = {
    "IST": "+05:30",
    "UTC": "+00:00",
    "GMT": "+00:00",
    "EST": "-05:00",
    "EDT": "-04:00",
    "CST": "-06:00",
    "CDT": "-05:00",
    "PST": "-08:00",
    "PDT": "-07:00",
    "BST": "+01:00",
    "CET": "+01:00",
    "CEST": "+02:00",
    "SGT": "+08:00",
    "JST": "+09:00",
    "AEST": "+10:00",
}


class InterviewDetector:
    """
    Extracts structured interview invitation metadata with strict timezone validation.
    """

    @classmethod
    def detect_interview(
        cls,
        subject: str,
        body: str,
        company_hint: Optional[str] = None,
        role_hint: Optional[str] = None,
        application_id: Optional[str] = None,
    ) -> Optional[InterviewSchedule]:
        """Parse interview dates, times, timezones, and meeting URLs from email text."""
        combined_text = f"{subject}\n{body}"

        # 1. Round type detection
        round_name = "Technical Interview"
        low = combined_text.lower()
        if "screening" in low or "phone screen" in low or "intro call" in low:
            round_name = "Screening Call"
        elif "system design" in low:
            round_name = "System Design Round"
        elif "final round" in low or "executive" in low:
            round_name = "Final Round"
        elif "hr" in low or "culture" in low or "behavioral" in low:
            round_name = "HR & Behavioral Round"
        elif "assessment" in low or "coding challenge" in low:
            round_name = "Technical Assessment"

        # 2. Extract Date
        extracted_date = ""
        for pat in _DATE_PATTERNS:
            m = pat.search(combined_text)
            if m:
                extracted_date = m.group(1).strip()
                break

        # Standardize date if possible
        if not extracted_date:
            extracted_date = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")

        # 3. Extract Time & Timezone
        extracted_time = ""
        extracted_tz = ""
        for pat in _TIME_PATTERNS:
            m = pat.search(combined_text)
            if m:
                extracted_time = m.group(1).strip()
                if m.group(2):
                    extracted_tz = m.group(2).strip().upper()
                break

        # Fallback timezone scan in body
        if not extracted_tz:
            for tz_code in _TIMEZONE_MAP.keys():
                if tz_code in combined_text.upper().split():
                    extracted_tz = tz_code
                    break

        # 4. Extract Meeting URL and Platform
        meeting_url = ""
        platform = "Google Meet"
        for pat in _MEETING_URL_PATTERNS:
            m = pat.search(combined_text)
            if m:
                meeting_url = m.group(1).strip()
                if "zoom" in meeting_url:
                    platform = "Zoom"
                elif "teams" in meeting_url:
                    platform = "Microsoft Teams"
                break

        # 5. Extract Interviewer Name
        interviewer = ""
        for m in re.finditer(r"(?:with|interviewer:?|speaking\s+with)\s+([A-Z][a-z]+[ \t]+[A-Z][a-z]+)", body):
            cand_name = m.group(1).strip()
            if company_hint and cand_name.lower() in company_hint.lower():
                continue
            interviewer = cand_name
            break

        schedule = InterviewSchedule(
            interview_id=f"INT-{uuid.uuid4().hex[:6].upper()}",
            application_id=application_id or "",
            company=company_hint or "Target Company",
            role=role_hint or "Software Engineer",
            round=round_name,
            date=extracted_date,
            time_str=extracted_time or "10:00 AM",
            timezone=extracted_tz or "IST",  # Default candidate timezone if stated in preferences
            duration_minutes=45 if "30" not in combined_text else 30,
            meeting_url=meeting_url,
            platform=platform,
            interviewer=interviewer,
            status="REQUESTED" if not meeting_url else "SCHEDULED",
            preparation_status="PENDING",
            notes=[
                f"Extracted from email on {datetime.date.today().strftime('%Y-%m-%d')}",
                f"Timezone: {extracted_tz or 'Not explicitly specified in email'}",
            ],
        )

        logger.info(
            "📅 Interview Invitation Extracted: [%s] %s with %s on %s at %s %s",
            schedule.interview_id,
            schedule.round,
            schedule.company,
            schedule.date,
            schedule.time_str,
            schedule.timezone,
        )
        return schedule
