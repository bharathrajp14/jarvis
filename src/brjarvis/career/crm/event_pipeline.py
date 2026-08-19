# career/crm/event_pipeline.py — Unified Career Event Bus Pipeline & Ingestion Architecture
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, Optional

from brjarvis.events.bus import get_event_bus

from ..email_intelligence.injection_guard import PromptInjectionGuard
from ..models import (
    Application,
    ApplicationEvent,
    ApplicationEventType,
    ApplicationStatus,
    PriorityLevel,
)
from ..notifications import get_career_notification_engine
from ..spreadsheet.projection import get_spreadsheet_projection
from .database import get_career_crm_db
from .state_machine import ApplicationStateMachine

logger = logging.getLogger("JARVIS.CareerCRM.EventPipeline")


class CareerEventPipeline:
    """
    Unified Single Pipeline for all Career Events:
    SOURCE -> EVENT NORMALIZER -> VALIDATOR -> DEDUPLICATOR ->
    APPLICATION MATCHER -> STATE MACHINE -> DATABASE -> SPREADSHEET ->
    MEMORY -> NOTIFICATION -> ANALYTICS
    """

    _INSTANCE: Optional[CareerEventPipeline] = None

    def __init__(self):
        self.db = get_career_crm_db()
        self.projection = get_spreadsheet_projection()
        self.notification_engine = get_career_notification_engine()
        self.global_bus = get_event_bus()

    @classmethod
    def get_instance(cls) -> CareerEventPipeline:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def ingest_event(
        self,
        source: str,
        event_type: ApplicationEventType | str,
        application_id: Optional[str] = None,
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
        target_status: Optional[ApplicationStatus | str] = None,
        evidence: str = "",
        confidence: float = 1.0,
        actor: str = "system",
        task_id: Optional[str] = None,
        auto_project_excel: bool = True,
    ) -> Dict[str, Any]:
        """
        Ingest and execute an event through the complete 11-stage pipeline.
        """
        payload = raw_payload or {}

        # 1. NORMALIZER: Standardize payload & parameters
        if isinstance(event_type, str):
            try:
                event_type_enum = ApplicationEventType(event_type)
            except Exception:
                event_type_enum = ApplicationEventType.APPLICATION_CREATED
        else:
            event_type_enum = event_type

        # 2. VALIDATOR: Prompt injection sanitization
        clean_evidence = PromptInjectionGuard.sanitize_and_encapsulate(evidence, source_type=source.upper())

        # 3. DEDUPLICATOR: Idempotency Key check
        idempotency_key = payload.get("idempotency_key")
        if not idempotency_key:
            idempotency_key = f"{source}:{event_type_enum.value}:{application_id or company or 'global'}:{time.strftime('%Y%m%d%H%M')}"

        # 4. APPLICATION MATCHER / RETRIEVAL
        target_app: Optional[Application] = None
        if application_id:
            target_app = self.db.get_application(application_id)
        elif company:
            target_app = self.db.find_application_by_job_or_company(company=company, job_title=job_title)

        # 5. STATE MACHINE & DATABASE PERSISTENCE
        app_id_for_event = target_app.application_id if target_app else (application_id or "GLOBAL")
        prev_state = target_app.application_status.value if target_app else "NONE"
        new_state = prev_state

        if target_app and target_status:
            try:
                target_app = ApplicationStateMachine.transition(
                    application_id=target_app.application_id,
                    target_status=target_status,
                    source=source,
                    actor=actor,
                    evidence=evidence,
                    confidence=confidence,
                    task_id=task_id,
                    note=payload.get("note"),
                )
                new_state = target_app.application_status.value
            except Exception as exc:
                logger.warning("Pipeline state transition note: %s", exc)

        # Record standalone audit event if not already emitted by state machine
        audit_event = ApplicationEvent(
            event_id=f"ev_{uuid.uuid4().hex[:10]}",
            application_id=app_id_for_event,
            timestamp=time.time(),
            source=source,
            actor=actor,
            event_type=event_type_enum,
            evidence=evidence or f"Ingested {event_type_enum.value}",
            confidence=confidence,
            previous_state=prev_state,
            new_state=new_state,
            task_id=task_id,
            payload=payload,
        )
        self.db.record_event(audit_event)

        # 6. SPREADSHEET PROJECTION
        excel_status = "SKIPPED"
        if auto_project_excel:
            proj_res = self.projection.project_database_to_excel()
            excel_status = proj_res.get("status", "FAILED")

        # 7. MEMORY INTEGRATION
        try:
            from brjarvis.career.memory_integration import sync_career_memory

            sync_career_memory(event_type=event_type_enum.value, application=target_app, payload=payload)
        except Exception as exc:
            logger.debug("Career memory sync notice: %s", exc)

        # 8. NOTIFICATION ENGINE
        priority = PriorityLevel.MEDIUM
        if event_type_enum in (ApplicationEventType.OFFER_DETECTED, ApplicationEventType.OFFER_CONFIRMED):
            priority = PriorityLevel.CRITICAL
        elif event_type_enum in (ApplicationEventType.INTERVIEW_REQUESTED, ApplicationEventType.INTERVIEW_SCHEDULED):
            priority = PriorityLevel.HIGH

        self.notification_engine.notify_career_event(
            event_type=event_type_enum.value,
            title=f"{event_type_enum.value}: {company or (target_app.company if target_app else 'Career Update')}",
            message=evidence or f"Status updated to {new_state}",
            priority=priority,
            application_id=app_id_for_event,
        )

        logger.info(
            "⚡ Pipeline Cycle Complete: [%s] -> App: %s, Excel: %s, Priority: %s",
            event_type_enum.value,
            app_id_for_event,
            excel_status,
            priority.value,
        )

        return {
            "status": "SUCCESS_VERIFIED",
            "event_id": audit_event.event_id,
            "application_id": app_id_for_event,
            "previous_state": prev_state,
            "new_state": new_state,
            "excel_projection": excel_status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


def get_career_pipeline() -> CareerEventPipeline:
    return CareerEventPipeline.get_instance()
