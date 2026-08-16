# career/email_intelligence/__init__.py — Career Email Intelligence Package
from __future__ import annotations

from career.email_intelligence.classifier import CareerEmailClassifier
from career.email_intelligence.matcher import EmailApplicationMatcher
from career.email_intelligence.offer_detector import OfferDetector
from career.email_intelligence.interview_detector import InterviewDetector
from career.email_intelligence.rejection_detector import RejectionDetector
from career.email_intelligence.injection_guard import PromptInjectionGuard
from career.email_intelligence.service import EmailCareerIntelligence, get_email_career_intelligence

__all__ = [
    "CareerEmailClassifier",
    "EmailApplicationMatcher",
    "OfferDetector",
    "InterviewDetector",
    "RejectionDetector",
    "PromptInjectionGuard",
    "EmailCareerIntelligence",
    "get_email_career_intelligence",
]
