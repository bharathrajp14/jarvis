# career/crm/state_machine.py — Deterministic Application State Machine & Transition Engine
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from .database import get_career_crm_db
from ..models import (
    Application,
    ApplicationEvent,
    ApplicationEventType,
    ApplicationStatus,
    PriorityLevel,
)

logger = logging.getLogger("JARVIS.CareerCRM.StateMachine")


# Deterministic transition graph
_VALID_TRANSITIONS: Dict[ApplicationStatus, Set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.PREPARING,
        ApplicationStatus.APPLICATION_OPENED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.PREPARING,
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.APPLICATION_OPENED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.PREPARING: {
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.APPLICATION_OPENED,
        ApplicationStatus.APPLICATION_IN_PROGRESS,
        ApplicationStatus.SUBMISSION_REQUESTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.MANUAL_ACTION_REQUIRED,
    },
    ApplicationStatus.READY_FOR_REVIEW: {
        ApplicationStatus.APPLICATION_OPENED,
        ApplicationStatus.APPLICATION_IN_PROGRESS,
        ApplicationStatus.SUBMISSION_REQUESTED,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_VERIFIED,
        ApplicationStatus.MANUAL_ACTION_REQUIRED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.APPLICATION_OPENED: {
        ApplicationStatus.APPLICATION_IN_PROGRESS,
        ApplicationStatus.SUBMISSION_REQUESTED,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_VERIFIED,
        ApplicationStatus.MANUAL_ACTION_REQUIRED,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.APPLICATION_IN_PROGRESS: {
        ApplicationStatus.SUBMISSION_REQUESTED,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_VERIFIED,
        ApplicationStatus.MANUAL_ACTION_REQUIRED,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.SUBMISSION_REQUESTED: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_VERIFIED,
        ApplicationStatus.MANUAL_ACTION_REQUIRED,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.SUBMISSION_VERIFIED,
        ApplicationStatus.RECRUITER_CONTACTED,
        ApplicationStatus.SCREENING,
        ApplicationStatus.INTERVIEW_REQUESTED,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.SUBMISSION_VERIFIED: {
        ApplicationStatus.RECRUITER_CONTACTED,
        ApplicationStatus.SCREENING,
        ApplicationStatus.INTERVIEW_REQUESTED,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.RECRUITER_CONTACTED: {
        ApplicationStatus.SCREENING,
        ApplicationStatus.INTERVIEW_REQUESTED,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.TECHNICAL_ROUND,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SCREENING: {
        ApplicationStatus.INTERVIEW_REQUESTED,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.TECHNICAL_ROUND,
        ApplicationStatus.FINAL_ROUND,
        ApplicationStatus.OFFER_RECEIVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW_REQUESTED: {
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.TECHNICAL_ROUND,
        ApplicationStatus.SCREENING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW_SCHEDULED: {
        ApplicationStatus.INTERVIEW_COMPLETED,
        ApplicationStatus.TECHNICAL_ROUND,
        ApplicationStatus.FINAL_ROUND,
        ApplicationStatus.OFFER_RECEIVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW_COMPLETED: {
        ApplicationStatus.TECHNICAL_ROUND,
        ApplicationStatus.FINAL_ROUND,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.OFFER_RECEIVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.TECHNICAL_ROUND: {
        ApplicationStatus.FINAL_ROUND,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.OFFER_RECEIVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.FINAL_ROUND: {
        ApplicationStatus.OFFER_RECEIVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER_RECEIVED: {
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFER_DECLINED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.OFFER_ACCEPTED: {
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER_DECLINED: {
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.MANUAL_ACTION_REQUIRED: {
        ApplicationStatus.APPLICATION_OPENED,
        ApplicationStatus.APPLICATION_IN_PROGRESS,
        ApplicationStatus.SUBMISSION_REQUESTED,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_VERIFIED,
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.FAILED: {
        ApplicationStatus.PREPARING,
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.APPLICATION_OPENED,
        ApplicationStatus.MANUAL_ACTION_REQUIRED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.REJECTED: {
        ApplicationStatus.DISCOVERED,  # Reopen if role re-listed or re-applied
    },
    ApplicationStatus.WITHDRAWN: {
        ApplicationStatus.DISCOVERED,
    },
    ApplicationStatus.UNKNOWN: {
        st for st in ApplicationStatus
    },
}


class ApplicationStateMachine:
    """
    Deterministic State Machine preventing unauthorized or arbitrary LLM status transitions.
    Generates immutable audit events for every transition.
    """

    @classmethod
    def can_transition(cls, current_status: ApplicationStatus, target_status: ApplicationStatus) -> Tuple[bool, str]:
        """Check whether transition from current_status to target_status is valid."""
        if current_status == target_status:
            return True, "No-op transition (status unchanged)."

        allowed = _VALID_TRANSITIONS.get(current_status, set())
        if target_status in allowed or current_status == ApplicationStatus.UNKNOWN:
            return True, f"Valid transition from {current_status.value} to {target_status.value}."

        return False, f"Invalid transition: Cannot advance directly from {current_status.value} to {target_status.value}."

    @classmethod
    def transition(
        cls,
        application_id: str,
        target_status: ApplicationStatus | str,
        source: str = "JARVIS",
        actor: str = "system",
        evidence: str = "",
        confidence: float = 1.0,
        task_id: Optional[str] = None,
        note: Optional[str] = None,
        confirmation_id: Optional[str] = None,
        confirmation_url: Optional[str] = None,
        force: bool = False,
    ) -> Application:
        """
        Execute deterministic state transition on an application entity.
        Persists update to database and emits an immutable ApplicationEvent.
        """
        db = get_career_crm_db()
        app = db.get_application(application_id)
        if not app:
            raise ValueError(f"Application ID '{application_id}' not found in canonical database.")

        if isinstance(target_status, str):
            try:
                target_status_enum = ApplicationStatus(target_status.upper())
            except Exception:
                raise ValueError(f"Invalid application status string: '{target_status}'. Must be a deterministic status.")
        else:
            target_status_enum = target_status

        prev_status = app.application_status

        # Validate transition unless force override is explicitly requested
        if not force:
            valid, reason = cls.can_transition(prev_status, target_status_enum)
            if not valid:
                logger.warning("🚫 State machine blocked invalid transition for %s: %s", application_id, reason)
                raise ValueError(reason)

        now = time.time()
        now_date_str = time.strftime("%Y-%m-%d")

        # Update application state
        app.application_status = target_status_enum
        app.last_updated = now

        if confirmation_id:
            app.confirmation_id = confirmation_id
        if confirmation_url:
            app.confirmation_url = confirmation_url

        if target_status_enum == ApplicationStatus.SHORTLISTED and not app.date_shortlisted:
            app.date_shortlisted = now_date_str
        elif target_status_enum == ApplicationStatus.PREPARING and not app.date_prepared:
            app.date_prepared = now_date_str
        elif target_status_enum in (ApplicationStatus.SUBMITTED, ApplicationStatus.SUBMISSION_VERIFIED):
            if not app.date_applied:
                app.date_applied = now_date_str
            app.submission_status = "SUBMITTED" if target_status_enum == ApplicationStatus.SUBMITTED else "VERIFIED"
            if target_status_enum == ApplicationStatus.SUBMISSION_VERIFIED and not app.date_verified:
                app.date_verified = now_date_str

        # Update priority based on high-value milestones
        if target_status_enum in (ApplicationStatus.OFFER_RECEIVED, ApplicationStatus.FINAL_ROUND):
            app.priority = PriorityLevel.CRITICAL
        elif target_status_enum in (ApplicationStatus.INTERVIEW_REQUESTED, ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.TECHNICAL_ROUND):
            app.priority = PriorityLevel.HIGH

        if note:
            app.notes.append(f"[{time.strftime('%Y-%m-%d %H:%M')}] {note}")

        # Persist updated Application
        db.save_application(app)

        # Map to canonical ApplicationEventType
        event_type_map = {
            ApplicationStatus.DISCOVERED: ApplicationEventType.APPLICATION_CREATED,
            ApplicationStatus.SHORTLISTED: ApplicationEventType.JOB_SHORTLISTED,
            ApplicationStatus.PREPARING: ApplicationEventType.APPLICATION_PREPARED,
            ApplicationStatus.APPLICATION_OPENED: ApplicationEventType.APPLICATION_OPENED,
            ApplicationStatus.SUBMITTED: ApplicationEventType.APPLICATION_SUBMITTED,
            ApplicationStatus.SUBMISSION_VERIFIED: ApplicationEventType.SUBMISSION_VERIFIED,
            ApplicationStatus.RECRUITER_CONTACTED: ApplicationEventType.RECRUITER_CONTACTED,
            ApplicationStatus.INTERVIEW_REQUESTED: ApplicationEventType.INTERVIEW_REQUESTED,
            ApplicationStatus.INTERVIEW_SCHEDULED: ApplicationEventType.INTERVIEW_SCHEDULED,
            ApplicationStatus.INTERVIEW_COMPLETED: ApplicationEventType.INTERVIEW_COMPLETED,
            ApplicationStatus.OFFER_RECEIVED: ApplicationEventType.OFFER_DETECTED,
            ApplicationStatus.OFFER_ACCEPTED: ApplicationEventType.OFFER_CONFIRMED,
            ApplicationStatus.REJECTED: ApplicationEventType.REJECTION_DETECTED,
        }
        event_type = event_type_map.get(target_status_enum, ApplicationEventType.APPLICATION_CREATED)

        # Append immutable audit event
        audit_event = ApplicationEvent(
            application_id=app.application_id,
            timestamp=now,
            source=source,
            actor=actor,
            event_type=event_type,
            evidence=evidence or f"Transitioned to {target_status_enum.value}",
            confidence=confidence,
            previous_state=prev_status.value,
            new_state=target_status_enum.value,
            task_id=task_id,
            payload={
                "company": app.company,
                "job_title": app.job_title,
                "note": note,
                "confirmation_id": confirmation_id,
            }
        )
        db.record_event(audit_event)

        logger.info("✅ State Transition Succeeded: [%s] %s -> %s (Source: %s, Conf: %.2f)",
                    app.application_id, prev_status.value, target_status_enum.value, source, confidence)
        return app
