# career/crm/database.py — Canonical Career Database & Immutable Event Store
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    Application,
    ApplicationEvent,
    ApplicationEventType,
    ApplicationStatus,
    CareerContact,
    EmailClassification,
    EmailEventRecord,
    FollowupRecord,
    InterviewSchedule,
    OfferCandidate,
    OfferStatus,
    PriorityLevel,
)
from brjarvis.memory.canonical_db import get_canonical_db

logger = logging.getLogger("JARVIS.CareerCRM.Database")


class CareerCRMDatabase:
    """
    Authoritative Single Source of Truth for Career State, Applications,
    Immutable Event Audits, Interviews, Offers, Follow-ups, and Contacts.
    """

    _INSTANCE: Optional[CareerCRMDatabase] = None
    _LOCK = threading.RLock()

    def __init__(self):
        self.db = get_canonical_db()
        self._init_tables()

    @classmethod
    def get_instance(cls) -> CareerCRMDatabase:
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregated counts of career applications, interviews, offers, and contacts."""
        apps = self.list_applications(limit=1000)
        interviews = self.list_interviews()
        offers = self.list_offers()
        contacts = self.list_contacts()
        return {
            "applications_count": len(apps),
            "interviews_count": len(interviews),
            "offers_count": len(offers),
            "contacts_count": len(contacts),
            "status_counts": self.count_applications_by_status(),
        }

    def _init_tables(self) -> None:
        """Initialize all relational tables and indexes for the Career CRM."""
        with self.db.get_connection() as conn:
            # 1. Canonical Applications Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS career_applications_v2 (
                    application_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    candidate_id TEXT NOT NULL,
                    job_id TEXT,
                    company TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    job_url TEXT,
                    source TEXT,
                    platform TEXT,
                    location TEXT,
                    employment_type TEXT,
                    salary TEXT,
                    currency TEXT,
                    job_description_hash TEXT,
                    match_score REAL DEFAULT 0.0,
                    resume_version TEXT,
                    cover_letter_version TEXT,
                    application_package_id TEXT,
                    application_method TEXT,
                    application_status TEXT NOT NULL,
                    submission_status TEXT,
                    confirmation_id TEXT,
                    confirmation_url TEXT,
                    date_discovered TEXT,
                    date_shortlisted TEXT,
                    date_prepared TEXT,
                    date_applied TEXT,
                    date_verified TEXT,
                    last_updated REAL NOT NULL,
                    next_followup TEXT,
                    priority TEXT DEFAULT 'MEDIUM',
                    notes_json TEXT,
                    data_json TEXT NOT NULL
                );
            """)

            # 2. Immutable Application Event Store
            conn.execute("""
                CREATE TABLE IF NOT EXISTS career_application_events (
                    event_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    source TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    evidence TEXT,
                    confidence REAL DEFAULT 1.0,
                    previous_state TEXT,
                    new_state TEXT,
                    task_id TEXT,
                    payload_json TEXT
                );
            """)

            # 3. Interviews Schedule Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS career_interviews (
                    interview_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    round TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time_str TEXT,
                    timezone TEXT,
                    utc_timestamp REAL,
                    local_timestamp REAL,
                    duration_minutes INTEGER DEFAULT 45,
                    meeting_url TEXT,
                    platform TEXT,
                    interviewer TEXT,
                    status TEXT NOT NULL,
                    preparation_status TEXT,
                    calendar_event_id TEXT,
                    notes_json TEXT,
                    data_json TEXT NOT NULL
                );
            """)

            # 4. Offers Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS career_offers (
                    offer_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    salary TEXT,
                    currency TEXT,
                    bonus TEXT,
                    benefits_json TEXT,
                    location TEXT,
                    work_mode TEXT,
                    joining_date TEXT,
                    offer_date TEXT,
                    expiry_date TEXT,
                    status TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    evidence TEXT,
                    conditions_json TEXT,
                    documents_requested_json TEXT,
                    contact_person TEXT,
                    offer_url TEXT,
                    attachment_names_json TEXT,
                    fact_analysis_json TEXT,
                    notes_json TEXT,
                    data_json TEXT NOT NULL
                );
            """)

            # 5. Follow-ups Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS career_followups (
                    followup_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    reason TEXT,
                    due_date TEXT NOT NULL,
                    priority TEXT DEFAULT 'MEDIUM',
                    status TEXT NOT NULL,
                    completed_date TEXT,
                    draft_subject TEXT,
                    draft_body TEXT,
                    notes_json TEXT,
                    data_json TEXT NOT NULL
                );
            """)

            # 6. Email Intelligence Records Table (Idempotency & Audit)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS career_email_records (
                    email_event_id TEXT PRIMARY KEY,
                    application_id TEXT,
                    message_id_hash TEXT UNIQUE NOT NULL,
                    provider TEXT NOT NULL,
                    sender TEXT,
                    sender_domain TEXT,
                    subject TEXT,
                    received_time TEXT,
                    classification TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    detected_event TEXT,
                    action_taken TEXT,
                    verification TEXT DEFAULT 'SUCCESS_VERIFIED',
                    processed_time REAL NOT NULL,
                    data_json TEXT NOT NULL
                );
            """)

            # 7. Contacts Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS career_contacts (
                    contact_id TEXT PRIMARY KEY,
                    application_id TEXT,
                    company TEXT NOT NULL,
                    name TEXT NOT NULL,
                    title TEXT,
                    email TEXT,
                    phone TEXT,
                    linkedin_url TEXT,
                    notes TEXT,
                    created_at REAL NOT NULL
                );
            """)

            # Indexes for fast lookup & reporting
            conn.execute("CREATE INDEX IF NOT EXISTS idx_apps_company ON career_applications_v2(company);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_apps_status ON career_applications_v2(application_status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_apps_updated ON career_applications_v2(last_updated);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_app_id ON career_application_events(application_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON career_application_events(event_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interviews_app ON career_interviews(application_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_offers_app ON career_offers(application_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_followups_due ON career_followups(due_date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_email_hash ON career_email_records(message_id_hash);")
            conn.commit()

    # ── Application CRUD ────────────────────────────────────────────────────────

    def save_application(self, app: Application) -> None:
        """Insert or update a canonical application entity."""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO career_applications_v2 (
                    application_id, task_id, candidate_id, job_id, company, job_title, job_url,
                    source, platform, location, employment_type, salary, currency, job_description_hash,
                    match_score, resume_version, cover_letter_version, application_package_id,
                    application_method, application_status, submission_status, confirmation_id,
                    confirmation_url, date_discovered, date_shortlisted, date_prepared, date_applied,
                    date_verified, last_updated, next_followup, priority, notes_json, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(application_id) DO UPDATE SET
                    task_id = excluded.task_id,
                    candidate_id = excluded.candidate_id,
                    job_id = excluded.job_id,
                    company = excluded.company,
                    job_title = excluded.job_title,
                    job_url = excluded.job_url,
                    source = excluded.source,
                    platform = excluded.platform,
                    location = excluded.location,
                    employment_type = excluded.employment_type,
                    salary = excluded.salary,
                    currency = excluded.currency,
                    job_description_hash = excluded.job_description_hash,
                    match_score = excluded.match_score,
                    resume_version = excluded.resume_version,
                    cover_letter_version = excluded.cover_letter_version,
                    application_package_id = excluded.application_package_id,
                    application_method = excluded.application_method,
                    application_status = excluded.application_status,
                    submission_status = excluded.submission_status,
                    confirmation_id = excluded.confirmation_id,
                    confirmation_url = excluded.confirmation_url,
                    date_discovered = excluded.date_discovered,
                    date_shortlisted = excluded.date_shortlisted,
                    date_prepared = excluded.date_prepared,
                    date_applied = excluded.date_applied,
                    date_verified = excluded.date_verified,
                    last_updated = excluded.last_updated,
                    next_followup = excluded.next_followup,
                    priority = excluded.priority,
                    notes_json = excluded.notes_json,
                    data_json = excluded.data_json;
            """, (
                app.application_id,
                app.task_id,
                app.candidate_id,
                app.job_id,
                app.company,
                app.job_title,
                app.job_url,
                app.source,
                app.platform,
                app.location,
                app.employment_type,
                app.salary,
                app.currency,
                app.job_description_hash,
                app.match_score,
                app.resume_version,
                app.cover_letter_version,
                app.application_package_id,
                app.application_method,
                app.application_status.value if isinstance(app.application_status, ApplicationStatus) else str(app.application_status),
                app.submission_status,
                app.confirmation_id,
                app.confirmation_url,
                app.date_discovered,
                app.date_shortlisted,
                app.date_prepared,
                app.date_applied,
                app.date_verified,
                app.last_updated,
                app.next_followup,
                app.priority.value if isinstance(app.priority, PriorityLevel) else str(app.priority),
                json.dumps(app.notes),
                json.dumps(app.to_dict()),
            ))
            conn.commit()

    def get_application(self, application_id: str) -> Optional[Application]:
        """Fetch application by application_id."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT data_json FROM career_applications_v2 WHERE application_id = ?", (application_id,))
            row = cursor.fetchone()
            if row:
                return Application.from_dict(json.loads(row["data_json"]))
        return None

    def find_application_by_job_or_company(self, company: str, job_title: Optional[str] = None, job_id: Optional[str] = None) -> Optional[Application]:
        """Search application by company name, job title, or job_id."""
        with self.db.get_connection() as conn:
            if job_id:
                cursor = conn.execute("SELECT data_json FROM career_applications_v2 WHERE job_id = ? LIMIT 1", (job_id,))
                row = cursor.fetchone()
                if row:
                    return Application.from_dict(json.loads(row["data_json"]))

            if company and job_title:
                cursor = conn.execute(
                    "SELECT data_json FROM career_applications_v2 WHERE LOWER(company) = LOWER(?) AND LOWER(job_title) = LOWER(?) LIMIT 1",
                    (company.strip(), job_title.strip())
                )
                row = cursor.fetchone()
                if row:
                    return Application.from_dict(json.loads(row["data_json"]))

            if company:
                cursor = conn.execute(
                    "SELECT data_json FROM career_applications_v2 WHERE LOWER(company) = LOWER(?) ORDER BY last_updated DESC LIMIT 1",
                    (company.strip(),)
                )
                row = cursor.fetchone()
                if row:
                    return Application.from_dict(json.loads(row["data_json"]))
        return None

    def list_applications(
        self,
        status: Optional[ApplicationStatus] = None,
        priority: Optional[PriorityLevel] = None,
        limit: int = 200,
        offset: int = 0
    ) -> List[Application]:
        """List applications with optional status and priority filters."""
        query = "SELECT data_json FROM career_applications_v2 WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND application_status = ?"
            params.append(status.value if isinstance(status, ApplicationStatus) else str(status))
        if priority:
            query += " AND priority = ?"
            params.append(priority.value if isinstance(priority, PriorityLevel) else str(priority))

        query += " ORDER BY last_updated DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [Application.from_dict(json.loads(row["data_json"])) for row in cursor.fetchall()]

    def count_applications_by_status(self) -> Dict[str, int]:
        """Get counts grouped by application status."""
        counts: Dict[str, int] = {st.value: 0 for st in ApplicationStatus}
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT application_status, COUNT(*) as cnt FROM career_applications_v2 GROUP BY application_status")
            for row in cursor.fetchall():
                counts[row["application_status"]] = row["cnt"]
        return counts

    # ── Event Store CRUD ────────────────────────────────────────────────────────

    def record_event(self, event: ApplicationEvent) -> None:
        """Append an immutable application audit event."""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO career_application_events (
                    event_id, application_id, timestamp, source, actor, event_type,
                    evidence, confidence, previous_state, new_state, task_id, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING;
            """, (
                event.event_id,
                event.application_id,
                event.timestamp,
                event.source,
                event.actor,
                event.event_type.value if isinstance(event.event_type, ApplicationEventType) else str(event.event_type),
                event.evidence,
                event.confidence,
                event.previous_state,
                event.new_state,
                event.task_id,
                json.dumps(event.payload),
            ))
            conn.commit()
        logger.debug("📝 Recorded ApplicationEvent [%s] for %s (%s -> %s)", event.event_type, event.application_id, event.previous_state, event.new_state)

    def get_events_for_application(self, application_id: str) -> List[ApplicationEvent]:
        """Fetch full chronological audit history for an application."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM career_application_events WHERE application_id = ? ORDER BY timestamp ASC",
                (application_id,)
            )
            events = []
            for row in cursor.fetchall():
                events.append(ApplicationEvent.from_dict({
                    "event_id": row["event_id"],
                    "application_id": row["application_id"],
                    "timestamp": row["timestamp"],
                    "source": row["source"],
                    "actor": row["actor"],
                    "event_type": row["event_type"],
                    "evidence": row["evidence"],
                    "confidence": row["confidence"],
                    "previous_state": row["previous_state"],
                    "new_state": row["new_state"],
                    "task_id": row["task_id"],
                    "payload": json.loads(row["payload_json"] or "{}"),
                }))
            return events

    def list_recent_events(self, limit: int = 50) -> List[ApplicationEvent]:
        """Fetch the most recent application events across all applications."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM career_application_events ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [
                ApplicationEvent.from_dict({
                    "event_id": row["event_id"],
                    "application_id": row["application_id"],
                    "timestamp": row["timestamp"],
                    "source": row["source"],
                    "actor": row["actor"],
                    "event_type": row["event_type"],
                    "evidence": row["evidence"],
                    "confidence": row["confidence"],
                    "previous_state": row["previous_state"],
                    "new_state": row["new_state"],
                    "task_id": row["task_id"],
                    "payload": json.loads(row["payload_json"] or "{}"),
                })
                for row in cursor.fetchall()
            ]

    # ── Interviews CRUD ────────────────────────────────────────────────────────

    def save_interview(self, interview: InterviewSchedule) -> None:
        """Insert or update an interview schedule record."""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO career_interviews (
                    interview_id, application_id, company, role, round, date, time_str,
                    timezone, utc_timestamp, local_timestamp, duration_minutes, meeting_url,
                    platform, interviewer, status, preparation_status, calendar_event_id,
                    notes_json, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(interview_id) DO UPDATE SET
                    round = excluded.round,
                    date = excluded.date,
                    time_str = excluded.time_str,
                    timezone = excluded.timezone,
                    utc_timestamp = excluded.utc_timestamp,
                    local_timestamp = excluded.local_timestamp,
                    duration_minutes = excluded.duration_minutes,
                    meeting_url = excluded.meeting_url,
                    platform = excluded.platform,
                    interviewer = excluded.interviewer,
                    status = excluded.status,
                    preparation_status = excluded.preparation_status,
                    calendar_event_id = excluded.calendar_event_id,
                    notes_json = excluded.notes_json,
                    data_json = excluded.data_json;
            """, (
                interview.interview_id,
                interview.application_id,
                interview.company,
                interview.role,
                interview.round,
                interview.date,
                interview.time_str,
                interview.timezone,
                interview.utc_timestamp,
                interview.local_timestamp,
                interview.duration_minutes,
                interview.meeting_url,
                interview.platform,
                interview.interviewer,
                interview.status,
                interview.preparation_status,
                interview.calendar_event_id,
                json.dumps(interview.notes),
                json.dumps(interview.to_dict()),
            ))
            conn.commit()

    def list_interviews(self, application_id: Optional[str] = None, limit: int = 100) -> List[InterviewSchedule]:
        """List scheduled and past interviews."""
        with self.db.get_connection() as conn:
            if application_id:
                cursor = conn.execute("SELECT data_json FROM career_interviews WHERE application_id = ? ORDER BY date DESC LIMIT ?", (application_id, limit))
            else:
                cursor = conn.execute("SELECT data_json FROM career_interviews ORDER BY date DESC, time_str DESC LIMIT ?", (limit,))
            
            interviews = []
            for row in cursor.fetchall():
                d = json.loads(row["data_json"])
                interviews.append(InterviewSchedule(**{k: v for k, v in d.items() if k in InterviewSchedule.__dataclass_fields__}))
            return interviews

    # ── Offers CRUD ────────────────────────────────────────────────────────────

    def save_offer(self, offer: OfferCandidate) -> None:
        """Insert or update an offer candidate/confirmed record."""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO career_offers (
                    offer_id, application_id, company, role, salary, currency, bonus,
                    benefits_json, location, work_mode, joining_date, offer_date, expiry_date,
                    status, confidence, evidence, conditions_json, documents_requested_json,
                    contact_person, offer_url, attachment_names_json, fact_analysis_json,
                    notes_json, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(offer_id) DO UPDATE SET
                    salary = excluded.salary,
                    currency = excluded.currency,
                    bonus = excluded.bonus,
                    benefits_json = excluded.benefits_json,
                    location = excluded.location,
                    work_mode = excluded.work_mode,
                    joining_date = excluded.joining_date,
                    offer_date = excluded.offer_date,
                    expiry_date = excluded.expiry_date,
                    status = excluded.status,
                    confidence = excluded.confidence,
                    evidence = excluded.evidence,
                    conditions_json = excluded.conditions_json,
                    documents_requested_json = excluded.documents_requested_json,
                    contact_person = excluded.contact_person,
                    offer_url = excluded.offer_url,
                    attachment_names_json = excluded.attachment_names_json,
                    fact_analysis_json = excluded.fact_analysis_json,
                    notes_json = excluded.notes_json,
                    data_json = excluded.data_json;
            """, (
                offer.offer_id,
                offer.application_id,
                offer.company,
                offer.role,
                offer.salary,
                offer.currency,
                offer.bonus,
                json.dumps(offer.benefits),
                offer.location,
                offer.work_mode,
                offer.joining_date,
                offer.offer_date,
                offer.expiry_date,
                offer.status.value if isinstance(offer.status, OfferStatus) else str(offer.status),
                offer.confidence,
                offer.evidence,
                json.dumps(offer.conditions),
                json.dumps(offer.documents_requested),
                offer.contact_person,
                offer.offer_url,
                json.dumps(offer.attachment_names),
                json.dumps(offer.fact_analysis),
                json.dumps(offer.notes),
                json.dumps(offer.to_dict()),
            ))
            conn.commit()

    def get_offer(self, offer_id: str) -> Optional[OfferCandidate]:
        """Fetch offer by offer_id."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT data_json FROM career_offers WHERE offer_id = ?", (offer_id,))
            row = cursor.fetchone()
            if row:
                d = json.loads(row["data_json"])
                st_raw = d.get("status", "OFFER_CANDIDATE")
                try:
                    st_enum = OfferStatus(st_raw)
                except Exception:
                    st_enum = OfferStatus.OFFER_CANDIDATE
                d["status"] = st_enum
                return OfferCandidate(**{k: v for k, v in d.items() if k in OfferCandidate.__dataclass_fields__})
        return None

    def list_offers(self, application_id: Optional[str] = None, limit: int = 100) -> List[OfferCandidate]:
        """List all tracked offer records."""
        with self.db.get_connection() as conn:
            if application_id:
                cursor = conn.execute("SELECT data_json FROM career_offers WHERE application_id = ? ORDER BY offer_date DESC LIMIT ?", (application_id, limit))
            else:
                cursor = conn.execute("SELECT data_json FROM career_offers ORDER BY offer_date DESC LIMIT ?", (limit,))

            offers = []
            for row in cursor.fetchall():
                d = json.loads(row["data_json"])
                st_raw = d.get("status", "OFFER_CANDIDATE")
                try:
                    st_enum = OfferStatus(st_raw)
                except Exception:
                    st_enum = OfferStatus.OFFER_CANDIDATE
                d["status"] = st_enum
                offers.append(OfferCandidate(**{k: v for k, v in d.items() if k in OfferCandidate.__dataclass_fields__}))
            return offers

    # ── Follow-ups CRUD ────────────────────────────────────────────────────────

    def save_followup(self, followup: FollowupRecord) -> None:
        """Insert or update a follow-up action record."""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO career_followups (
                    followup_id, application_id, company, role, reason, due_date,
                    priority, status, completed_date, draft_subject, draft_body,
                    notes_json, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(followup_id) DO UPDATE SET
                    reason = excluded.reason,
                    due_date = excluded.due_date,
                    priority = excluded.priority,
                    status = excluded.status,
                    completed_date = excluded.completed_date,
                    draft_subject = excluded.draft_subject,
                    draft_body = excluded.draft_body,
                    notes_json = excluded.notes_json,
                    data_json = excluded.data_json;
            """, (
                followup.followup_id,
                followup.application_id,
                followup.company,
                followup.role,
                followup.reason,
                followup.due_date,
                followup.priority.value if isinstance(followup.priority, PriorityLevel) else str(followup.priority),
                followup.status,
                followup.completed_date,
                followup.draft_subject,
                followup.draft_body,
                json.dumps(followup.notes),
                json.dumps(followup.to_dict()),
            ))
            conn.commit()

    def list_followups(self, status: Optional[str] = None, limit: int = 100) -> List[FollowupRecord]:
        """List pending or completed follow-ups."""
        with self.db.get_connection() as conn:
            if status:
                cursor = conn.execute("SELECT data_json FROM career_followups WHERE status = ? ORDER BY due_date ASC LIMIT ?", (status, limit))
            else:
                cursor = conn.execute("SELECT data_json FROM career_followups ORDER BY due_date ASC LIMIT ?", (limit,))

            followups = []
            for row in cursor.fetchall():
                d = json.loads(row["data_json"])
                pri_raw = d.get("priority", "MEDIUM")
                try:
                    pri_enum = PriorityLevel(pri_raw)
                except Exception:
                    pri_enum = PriorityLevel.MEDIUM
                d["priority"] = pri_enum
                followups.append(FollowupRecord(**{k: v for k, v in d.items() if k in FollowupRecord.__dataclass_fields__}))
            return followups

    # ── Email Intelligence & Idempotency CRUD ──────────────────────────────────

    def record_email_event(self, rec: EmailEventRecord) -> bool:
        """Record an email intelligence event. Returns False if duplicate message_id_hash."""
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO career_email_records (
                        email_event_id, application_id, message_id_hash, provider, sender,
                        sender_domain, subject, received_time, classification, confidence,
                        detected_event, action_taken, verification, processed_time, data_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec.email_event_id,
                    rec.application_id,
                    rec.message_id_hash,
                    rec.provider,
                    rec.sender,
                    rec.sender_domain,
                    rec.subject,
                    rec.received_time,
                    rec.classification.value if isinstance(rec.classification, EmailClassification) else str(rec.classification),
                    rec.confidence,
                    rec.detected_event,
                    rec.action_taken,
                    rec.verification,
                    rec.processed_time,
                    json.dumps(rec.to_dict()),
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            logger.debug("Email record already processed for message hash: %s", rec.message_id_hash)
            return False

    def is_email_processed(self, message_id_hash: str) -> bool:
        """Check if an email message hash has already been processed (idempotency guard)."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM career_email_records WHERE message_id_hash = ? LIMIT 1", (message_id_hash,))
            return cursor.fetchone() is not None

    def list_email_records(self, limit: int = 100) -> List[EmailEventRecord]:
        """List processed career email records."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT data_json FROM career_email_records ORDER BY processed_time DESC LIMIT ?", (limit,))
            records = []
            for row in cursor.fetchall():
                d = json.loads(row["data_json"])
                cls_raw = d.get("classification", "IRRELEVANT")
                try:
                    cls_enum = EmailClassification(cls_raw)
                except Exception:
                    cls_enum = EmailClassification.IRRELEVANT
                d["classification"] = cls_enum
                records.append(EmailEventRecord(**{k: v for k, v in d.items() if k in EmailEventRecord.__dataclass_fields__}))
            return records

    # ── Contacts CRUD ──────────────────────────────────────────────────────────

    def save_contact(self, contact: CareerContact) -> None:
        """Save a hiring manager or recruiter contact."""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO career_contacts (
                    contact_id, application_id, company, name, title, email, phone,
                    linkedin_url, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(contact_id) DO UPDATE SET
                    application_id = excluded.application_id,
                    company = excluded.company,
                    name = excluded.name,
                    title = excluded.title,
                    email = excluded.email,
                    phone = excluded.phone,
                    linkedin_url = excluded.linkedin_url,
                    notes = excluded.notes;
            """, (
                contact.contact_id,
                contact.application_id,
                contact.company,
                contact.name,
                contact.title,
                contact.email,
                contact.phone,
                contact.linkedin_url,
                contact.notes,
                contact.created_at,
            ))
            conn.commit()

    def list_contacts(self, company: Optional[str] = None, limit: int = 100) -> List[CareerContact]:
        """List contacts, optionally filtered by company."""
        with self.db.get_connection() as conn:
            if company:
                cursor = conn.execute("SELECT * FROM career_contacts WHERE LOWER(company) = LOWER(?) ORDER BY created_at DESC LIMIT ?", (company.strip(), limit))
            else:
                cursor = conn.execute("SELECT * FROM career_contacts ORDER BY created_at DESC LIMIT ?", (limit,))

            contacts = []
            for row in cursor.fetchall():
                contacts.append(CareerContact(
                    contact_id=row["contact_id"],
                    application_id=row["application_id"],
                    company=row["company"],
                    name=row["name"],
                    title=row["title"] or "Recruiter",
                    email=row["email"] or "",
                    phone=row["phone"] or "",
                    linkedin_url=row["linkedin_url"] or "",
                    notes=row["notes"] or "",
                    created_at=row["created_at"],
                ))
            return contacts


def get_career_crm_db() -> CareerCRMDatabase:
    """Convenience getter for the Career CRM Database singleton."""
    return CareerCRMDatabase.get_instance()
