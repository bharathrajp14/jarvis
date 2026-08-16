# career/crm/__init__.py — Canonical Career CRM & State Engine for BR JARVIS
from __future__ import annotations

from career.crm.database import CareerCRMDatabase, get_career_crm_db
from career.crm.state_machine import ApplicationStateMachine
from career.crm.event_pipeline import CareerEventPipeline, get_career_pipeline
from career.crm.followup_engine import FollowupEngine, get_followup_engine

__all__ = [
    "CareerCRMDatabase",
    "get_career_crm_db",
    "ApplicationStateMachine",
    "CareerEventPipeline",
    "get_career_pipeline",
    "FollowupEngine",
    "get_followup_engine",
]
