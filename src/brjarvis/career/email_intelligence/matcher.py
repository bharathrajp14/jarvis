# career/email_intelligence/matcher.py — Multi-Factor Application Matcher
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..crm.database import get_career_crm_db
from ..models import Application

logger = logging.getLogger("JARVIS.EmailIntelligence.Matcher")


@dataclass
class ApplicationMatchResult:
    matched_application: Optional[Application] = None
    application_id: Optional[str] = None
    company: str = ""
    job_title: str = ""
    confidence: float = 0.0
    match_factors: List[str] = field(default_factory=list)
    needs_review: bool = False
    review_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "company": self.company,
            "job_title": self.job_title,
            "confidence": round(self.confidence, 2),
            "match_factors": self.match_factors,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
        }


class EmailApplicationMatcher:
    """
    Matches incoming parsed career emails to existing active applications in the CRM.
    Computes multi-factor confidence and enforces human review thresholds.
    """

    CONFIDENCE_AUTO_MATCH_THRESHOLD = 0.70

    @classmethod
    def match_email(
        cls,
        sender: str,
        subject: str,
        body: str,
        company_hint: Optional[str] = None,
        role_hint: Optional[str] = None,
        sender_domain: Optional[str] = None,
    ) -> ApplicationMatchResult:
        """Execute multi-signal matching against canonical application database."""
        db = get_career_crm_db()
        apps = db.list_applications(limit=500)

        if not apps:
            return ApplicationMatchResult(
                confidence=0.0,
                needs_review=True,
                review_reason="No tracked applications found in database."
            )

        text_to_search = f"{subject}\n{body}\n{sender}".lower()

        # 1. Direct Application ID match (e.g. APP-00142, REQ-8491)
        for app in apps:
            if app.application_id and app.application_id.lower() in text_to_search:
                return ApplicationMatchResult(
                    matched_application=app,
                    application_id=app.application_id,
                    company=app.company,
                    job_title=app.job_title,
                    confidence=0.98,
                    match_factors=[f"exact_application_id_match:{app.application_id}"],
                    needs_review=False,
                )
            if app.confirmation_id and app.confirmation_id.lower() in text_to_search:
                return ApplicationMatchResult(
                    matched_application=app,
                    application_id=app.application_id,
                    company=app.company,
                    job_title=app.job_title,
                    confidence=0.97,
                    match_factors=[f"exact_confirmation_id_match:{app.confirmation_id}"],
                    needs_review=False,
                )

        best_app: Optional[Application] = None
        best_score: float = 0.0
        best_factors: List[str] = []

        for app in apps:
            score = 0.0
            factors: List[str] = []

            co_lower = app.company.lower().strip()
            title_lower = app.job_title.lower().strip()

            # Company name match
            if co_lower and co_lower in text_to_search:
                score += 0.45
                factors.append(f"company_name_found:{app.company}")
            elif company_hint and co_lower in company_hint.lower():
                score += 0.40
                factors.append(f"company_hint_match:{company_hint}")

            # Job title / Role match
            if title_lower and title_lower in text_to_search:
                score += 0.35
                factors.append(f"job_title_exact_match:{app.job_title}")
            elif role_hint and title_lower in role_hint.lower():
                score += 0.30
                factors.append(f"job_title_hint_match:{role_hint}")
            else:
                # Key role tokens match (e.g. "Software Engineer", "AI Engineer")
                role_words = [w for w in title_lower.split() if len(w) > 3 and w not in ("senior", "junior", "lead", "staff", "the", "and")]
                matched_words = [w for w in role_words if w in text_to_search]
                if matched_words:
                    token_score = min(0.25, len(matched_words) * 0.10)
                    score += token_score
                    factors.append(f"role_keywords_matched:{matched_words}")

            # Sender domain match with company
            if sender_domain and co_lower and co_lower in sender_domain:
                score += 0.20
                factors.append(f"sender_domain_matches_company:{sender_domain}")

            if score > best_score:
                best_score = score
                best_app = app
                best_factors = factors

        if best_app and best_score >= cls.CONFIDENCE_AUTO_MATCH_THRESHOLD:
            return ApplicationMatchResult(
                matched_application=best_app,
                application_id=best_app.application_id,
                company=best_app.company,
                job_title=best_app.job_title,
                confidence=min(1.0, best_score),
                match_factors=best_factors,
                needs_review=False,
            )

        if best_app and best_score >= 0.35:
            return ApplicationMatchResult(
                matched_application=best_app,
                application_id=best_app.application_id,
                company=best_app.company,
                job_title=best_app.job_title,
                confidence=round(best_score, 2),
                match_factors=best_factors,
                needs_review=True,
                review_reason=f"Confidence {round(best_score*100)}% below automatic threshold ({int(cls.CONFIDENCE_AUTO_MATCH_THRESHOLD*100)}%). Requires human verification.",
            )

        return ApplicationMatchResult(
            confidence=0.0,
            needs_review=True,
            review_reason="No matching application found with sufficient confidence.",
        )
