# career/email_intelligence/__init__.py — Career Email Intelligence Package
from __future__ import annotations

from .classifier import CareerEmailClassifier
from .injection_guard import PromptInjectionGuard
from .interview_detector import InterviewDetector
from .matcher import EmailApplicationMatcher
from .offer_detector import OfferDetector
from .rejection_detector import RejectionDetector
from .service import EmailCareerIntelligence, get_email_career_intelligence

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
