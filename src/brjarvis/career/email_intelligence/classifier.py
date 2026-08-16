# career/email_intelligence/classifier.py — 16-Category Career Email Classifier
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..models import EmailClassification

logger = logging.getLogger("JARVIS.EmailIntelligence.Classifier")

_ATS_DOMAINS = {
    "greenhouse-mail.io", "gh-mail.io", "greenhouse.io",
    "lever.co", "hire.lever.co",
    "ashbyhq.com", "ashby-mail.com",
    "myworkday.com", "workday.com",
    "smartrecruiters.com",
    "icims.com",
    "jobvite.com",
    "bamboohr.com",
    "recruitee.com",
    "workablemail.com", "workable.com",
}


@dataclass
class ClassificationResult:
    classification: EmailClassification
    confidence: float
    detected_features: List[str]
    company_hint: Optional[str] = None
    role_hint: Optional[str] = None
    evidence_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification": self.classification.value,
            "confidence": round(self.confidence, 2),
            "detected_features": self.detected_features,
            "company_hint": self.company_hint,
            "role_hint": self.role_hint,
            "evidence_snippet": self.evidence_snippet,
        }


class CareerEmailClassifier:
    """
    Deterministic Multi-Signal Classifier for Career & Recruitment Communications.
    """

    @classmethod
    def classify_email(
        cls,
        sender: str,
        subject: str,
        body: str,
        sender_domain: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> ClassificationResult:
        """Classify incoming email across 16 categories using multi-signal analysis."""
        sender_clean = sender.lower().strip()
        subj_clean = subject.lower().strip()
        body_clean = body.lower().strip()
        domain = (sender_domain or (sender.split("@")[-1] if "@" in sender else "")).lower().strip()
        att_list = [a.lower() for a in (attachments or [])]

        features: List[str] = []
        company_hint: Optional[str] = None
        role_hint: Optional[str] = None

        is_ats = any(ats in domain for ats in _ATS_DOMAINS)
        if is_ats:
            features.append(f"ats_sender_domain:{domain}")

        # Extract potential company name from domain or subject
        if not is_ats and "." in domain and domain not in ("gmail.com", "outlook.com", "yahoo.com", "hotmail.com"):
            company_hint = domain.split(".")[0].title()

        # ── 1. OFFER & OFFER UPDATE ──────────────────────────────────────────
        offer_strong = [
            "offer of employment", "job offer", "pleased to offer you", "congratulations on your offer",
            "formal offer letter", "official offer letter", "offer package", "employment agreement",
            "compensation package", "offer details"
        ]
        if any(kw in subj_clean for kw in ("offer letter", "job offer", "offer of employment")) or \
           any(kw in body_clean for kw in offer_strong) or \
           any("offer" in a for a in att_list):
            
            features.append("offer_keywords_matched")
            if any("revised" in subj_clean or "update" in subj_clean for _ in [1]):
                return ClassificationResult(
                    classification=EmailClassification.OFFER_UPDATE,
                    confidence=0.92,
                    detected_features=features + ["offer_revision"],
                    company_hint=company_hint,
                    evidence_snippet=subject[:120],
                )
            return ClassificationResult(
                classification=EmailClassification.OFFER,
                confidence=0.95,
                detected_features=features + ["offer_formal"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 2. INTERVIEW INVITATIONS, CONFIRMATIONS & RESCHEDULES ────────────
        if any(kw in subj_clean or kw in body_clean for kw in ("reschedule your interview", "interview reschedule", "rescheduled:")):
            return ClassificationResult(
                classification=EmailClassification.INTERVIEW_RESCHEDULE,
                confidence=0.90,
                detected_features=features + ["interview_reschedule"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        if any(kw in subj_clean for kw in ("interview confirmed", "interview confirmation", "calendar invite", "invitation: interview")):
            return ClassificationResult(
                classification=EmailClassification.INTERVIEW_CONFIRMATION,
                confidence=0.93,
                detected_features=features + ["interview_confirmation"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        if any(kw in subj_clean or kw in body_clean for kw in ("reminder: upcoming interview", "interview reminder")):
            return ClassificationResult(
                classification=EmailClassification.INTERVIEW_REMINDER,
                confidence=0.88,
                detected_features=features + ["interview_reminder"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        interview_invite_phrases = [
            "invitation to interview", "interview invitation", "invite you for an interview",
            "schedule an interview", "like to invite you for a technical interview",
            "technical round", "system design interview", "final round interview",
            "coding interview", "virtual interview with", "screening interview",
            "speaking with our team", "next steps in the interview process", "technical interview"
        ]
        if any(kw in subj_clean for kw in ("interview", "technical discussion", "technical round", "chat with", "next steps")) or \
           any(p in body_clean for p in interview_invite_phrases):
            return ClassificationResult(
                classification=EmailClassification.INTERVIEW_REQUEST,
                confidence=0.91,
                detected_features=features + ["interview_invitation"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 3. TECHNICAL TEST & ASSESSMENT ───────────────────────────────────
        test_phrases = [
            "technical assessment", "coding challenge", "online test", "take-home assessment",
            "hackerrank", "codesignal", "karat", "codility", "assessment invitation",
            "skills assessment", "complete the technical test"
        ]
        if any(kw in subj_clean or kw in body_clean for kw in test_phrases):
            return ClassificationResult(
                classification=EmailClassification.TECHNICAL_TEST if "technical" in subj_clean or "coding" in subj_clean else EmailClassification.ASSESSMENT,
                confidence=0.90,
                detected_features=features + ["technical_assessment"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 4. SCREENING REQUEST ─────────────────────────────────────────────
        screening_phrases = [
            "quick phone screen", "introductory call", "screening call", "recruiter phone screen",
            "30-minute intro call", "15-minute chat", "initial conversation", "time to connect for a call"
        ]
        if any(kw in subj_clean for kw in ("phone screen", "intro call", "introductory chat")) or \
           any(p in body_clean for p in screening_phrases):
            return ClassificationResult(
                classification=EmailClassification.SCREENING_REQUEST,
                confidence=0.88,
                detected_features=features + ["screening_request"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 5. REJECTION ─────────────────────────────────────────────────────
        rejection_phrases = [
            "thank you for your interest", "not moving forward", "not be moving forward",
            "not be proceeding", "pursue other candidates", "decided to move forward with other",
            "position has been filled", "unfortunate to inform you", "not selected for an interview",
            "wish you the best in your job search", "after careful consideration", "unable to offer"
        ]
        if (any(p in body_clean for p in ("not moving forward", "not be moving forward", "not be proceeding", "pursue other", "position has been filled", "unable to offer", "not selected")) or \
           ("thank you for your interest" in body_clean and any(neg in body_clean for neg in ("however", "not", "unfortunately", "other candidates"))) or \
           ("careful consideration" in body_clean and any(neg in body_clean for neg in ("however", "not", "unable", "cannot")))) or \
           (any(kw in subj_clean for kw in ("status of your application", "update on your application", "your application for", "your application to")) and any(neg in body_clean for neg in ("not", "unfortunately", "other candidates"))):
            return ClassificationResult(
                classification=EmailClassification.REJECTION,
                confidence=0.94,
                detected_features=features + ["rejection_notice"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 6. APPLICATION CONFIRMATION & RECEIVED ───────────────────────────
        app_confirm_phrases = [
            "thank you for applying", "we have received your application", "application received",
            "application confirmation", "successfully submitted your application",
            "received your resume", "your application has been submitted"
        ]
        if any(kw in subj_clean for kw in ("application received", "thank you for applying", "application submitted")) or \
           any(p in body_clean for p in app_confirm_phrases):
            return ClassificationResult(
                classification=EmailClassification.APPLICATION_CONFIRMATION if "confirmation" in subj_clean or "submitted" in subj_clean else EmailClassification.APPLICATION_RECEIVED,
                confidence=0.94,
                detected_features=features + ["application_receipt"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 7. RECRUITER DIRECT CONTACT / SOURCING ───────────────────────────
        recruiter_phrases = [
            "came across your profile", "impressed by your background", "exciting role at",
            "open role at", "talent acquisition partner at", "recruiter at", "reach out regarding a position"
        ]
        if any(p in body_clean for p in recruiter_phrases) or \
           any(kw in subj_clean for kw in ("opportunity at", "role at", "exciting position")):
            return ClassificationResult(
                classification=EmailClassification.RECRUITER_CONTACT,
                confidence=0.82,
                detected_features=features + ["recruiter_outreach"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 8. WITHDRAWAL ────────────────────────────────────────────────────
        if any(kw in subj_clean or kw in body_clean for kw in ("withdrawn your application", "application withdrawal confirmed", "withdrew from")):
            return ClassificationResult(
                classification=EmailClassification.WITHDRAWAL,
                confidence=0.90,
                detected_features=features + ["withdrawal_confirmation"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 9. GENERAL RECRUITING & NEWSLETTER ────────────────────────────────
        if is_ats or any(kw in subj_clean for kw in ("career", "job", "opening", "hiring")):
            return ClassificationResult(
                classification=EmailClassification.GENERAL_RECRUITING,
                confidence=0.60,
                detected_features=features + ["general_recruiting"],
                company_hint=company_hint,
                evidence_snippet=subject[:120],
            )

        # ── 10. IRRELEVANT ───────────────────────────────────────────────────
        return ClassificationResult(
            classification=EmailClassification.IRRELEVANT,
            confidence=0.95,
            detected_features=["no_career_patterns_matched"],
            evidence_snippet=subject[:80],
        )
