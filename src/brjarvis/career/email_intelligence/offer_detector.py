# career/email_intelligence/offer_detector.py — Conservative Offer Detection & Document Analysis Engine
from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from ..models import OfferCandidate, OfferStatus

logger = logging.getLogger("JARVIS.EmailIntelligence.OfferDetector")

_SALARY_REGEX = re.compile(
    r"(\$|₹|£|€|USD|INR|EUR|GBP)\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+k?)\s?(?:per\s+(?:annum|year|month)|/yr|/month|p\.a\.|annual)?",
    re.IGNORECASE,
)
_EXPIRY_REGEX = re.compile(
    r"(?:expires|valid\s+(?:until|through)|deadline|respond\s+by|accept\s+by)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)
_JOINING_REGEX = re.compile(
    r"(?:start\s+date|joining\s+date|commence\s+employment|first\s+day)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.IGNORECASE,
)


class OfferDetector:
    """
    Conservative Offer Detection & Offer Document Analysis Engine.
    Enforces strict staging (OFFER_CANDIDATE -> OFFER_DETECTED -> OFFER_CONFIRMED)
    and transparent distinction between Extracted Facts and Interpretations.
    """

    @classmethod
    def analyze_offer_content(
        cls,
        subject: str,
        body: str,
        sender: str = "",
        attachments: Optional[List[str]] = None,
        application_id: Optional[str] = None,
        company_hint: Optional[str] = None,
        role_hint: Optional[str] = None,
    ) -> Optional[OfferCandidate]:
        """
        Extract offer compensation, dates, conditions, and risk flags.
        Returns OfferCandidate in staged state.
        """
        combined_text = f"{subject}\n{body}"

        # 1. Detect salary & currency
        salary_match = _SALARY_REGEX.search(combined_text)
        salary_str = ""
        currency_str = "USD"
        if salary_match:
            raw_curr = salary_match.group(1).upper()
            raw_val = salary_match.group(2)
            curr_map = {"$": "USD", "₹": "INR", "£": "GBP", "€": "EUR"}
            currency_str = curr_map.get(raw_curr, raw_curr)
            salary_str = f"{currency_str} {raw_val}"

        # 2. Detect dates
        expiry_match = _EXPIRY_REGEX.search(combined_text)
        expiry_date = expiry_match.group(1) if expiry_match else ""

        joining_match = _JOINING_REGEX.search(combined_text)
        joining_date = joining_match.group(1) if joining_match else ""

        # 3. Detect bonus & benefits
        bonus_str = ""
        if "sign-on bonus" in combined_text.lower() or "signing bonus" in combined_text.lower():
            b_match = _SALARY_REGEX.search(combined_text[combined_text.lower().find("bonus") :])
            bonus_str = b_match.group(0) if b_match else "Signing Bonus Mentioned"

        benefits: List[str] = []
        if "health" in combined_text.lower() or "medical" in combined_text.lower():
            benefits.append("Health & Medical Insurance")
        if (
            "401k" in combined_text.lower()
            or "provident fund" in combined_text.lower()
            or "pension" in combined_text.lower()
        ):
            benefits.append("Retirement / 401(k) / PF")
        if (
            "equity" in combined_text.lower()
            or "rsu" in combined_text.lower()
            or "stock options" in combined_text.lower()
        ):
            benefits.append("Equity / RSUs")
        if "paid time off" in combined_text.lower() or "pto" in combined_text.lower():
            benefits.append("Paid Time Off")

        # 4. Work mode
        work_mode = "Remote"
        if "hybrid" in combined_text.lower():
            work_mode = "Hybrid"
        elif (
            "on-site" in combined_text.lower()
            or "onsite" in combined_text.lower()
            or "in-office" in combined_text.lower()
        ):
            work_mode = "Onsite"

        # 5. Conditions & Documents requested
        conditions: List[str] = []
        if any(
            w in combined_text.lower()
            for w in ("background check", "background verification", "background screening", "contingent")
        ):
            conditions.append("Contingent on successful background verification")
        if "reference" in combined_text.lower():
            conditions.append("Reference checks required")
        if "drug screen" in combined_text.lower():
            conditions.append("Pre-employment drug screening required")
        if "sponsorship" in combined_text.lower() or "work authorization" in combined_text.lower():
            conditions.append("Proof of legal work authorization required")

        # 6. Transparent fact analysis (Fact vs Interpretation)
        fact_analysis: Dict[str, Any] = {
            "extracted_facts": {
                "salary": salary_str or "Not explicitly stated in body",
                "joining_date": joining_date or "To be agreed / Not found",
                "offer_expiry": expiry_date or "Not specified",
                "bonus": bonus_str or "None specified",
                "work_mode": work_mode,
            },
            "interpretation_flags": {
                "salary_specified": bool(salary_str),
                "expiry_urgent": bool(expiry_date),
                "has_contingencies": bool(conditions),
                "missing_terms": [
                    k
                    for k, v in [("salary", salary_str), ("joining_date", joining_date), ("expiry_date", expiry_date)]
                    if not v
                ],
            },
        }

        # Calculate evidence confidence
        confidence = 0.60
        if salary_str:
            confidence += 0.20
        if expiry_date or joining_date:
            confidence += 0.15
        if attachments and any("offer" in a.lower() for a in attachments):
            confidence += 0.15

        status = OfferStatus.OFFER_DETECTED if confidence >= 0.85 else OfferStatus.OFFER_CANDIDATE

        offer = OfferCandidate(
            offer_id=f"OFF-{uuid.uuid4().hex[:6].upper()}",
            application_id=application_id or "",
            company=company_hint or "Hiring Company",
            role=role_hint or "Offered Role",
            salary=salary_str,
            currency=currency_str,
            bonus=bonus_str,
            benefits=benefits,
            location="Remote" if work_mode == "Remote" else "Company Office",
            work_mode=work_mode,
            joining_date=joining_date,
            expiry_date=expiry_date,
            status=status,
            confidence=min(1.0, confidence),
            evidence=f"Extracted from email: '{subject[:80]}'",
            conditions=conditions,
            attachment_names=attachments or [],
            fact_analysis=fact_analysis,
            notes=[f"Detected on {time.strftime('%Y-%m-%d %H:%M')} (Confidence: {round(confidence * 100)}%)"],
        )

        logger.info(
            "💼 Offer Candidate Detected: [%s] for %s (%s) — Status: %s",
            offer.offer_id,
            offer.company,
            offer.role,
            offer.status.value,
        )
        return offer
