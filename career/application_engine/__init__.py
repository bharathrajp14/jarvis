# career/application_engine/__init__.py — Application Engine Subsystem Package
from __future__ import annotations

from career.application_engine.policy import PlatformPolicyEngine, KNOWN_PLATFORM_POLICIES
from career.application_engine.questions import QuestionEngine
from career.application_engine.package_builder import ApplicationPackageBuilder
from career.application_engine.duplicate_guard import DuplicateApplicationGuard
from career.application_engine.tracker import ApplicationTracker, get_instance as get_application_tracker
from career.application_engine.verifier import ApplicationSubmissionVerifier
from career.application_engine.assistant import ManualApplicationAssistant

__all__ = [
    "PlatformPolicyEngine",
    "KNOWN_PLATFORM_POLICIES",
    "QuestionEngine",
    "ApplicationPackageBuilder",
    "DuplicateApplicationGuard",
    "ApplicationTracker",
    "get_application_tracker",
    "ApplicationSubmissionVerifier",
    "ManualApplicationAssistant",
]
