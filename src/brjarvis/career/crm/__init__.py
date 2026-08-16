# career/crm/__init__.py — Canonical Career CRM & State Engine for BR JARVIS
from __future__ import annotations

from .database import CareerCRMDatabase, get_career_crm_db
from .state_machine import ApplicationStateMachine
from .event_pipeline import CareerEventPipeline, get_career_pipeline
from .followup_engine import FollowupEngine, get_followup_engine

__all__ = [
    "CareerCRMDatabase",
    "get_career_crm_db",
    "ApplicationStateMachine",
    "CareerEventPipeline",
    "get_career_pipeline",
    "FollowupEngine",
    "get_followup_engine",
]
