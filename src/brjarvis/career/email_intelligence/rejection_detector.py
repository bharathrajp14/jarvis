# career/email_intelligence/rejection_detector.py — Rejection Detection & Discrimination Engine
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.EmailIntelligence.RejectionDetector")

_REJECTION_EVIDENCE_PATTERNS = [
    re.compile(r"thank you for your interest.*?however.*?(?:not moving forward|decided to pursue other|other candidates)", re.IGNORECASE | re.DOTALL),
    re.compile(r"we will not be (?:moving|proceeding) forward", re.IGNORECASE),
    re.compile(r"position has been (?:filled|closed|cancelled)", re.IGNORECASE),
    re.compile(r"not selected for an interview", re.IGNORECASE),
    re.compile(r"after careful (?:review|consideration).*?(?:unable to offer|decided not to proceed)", re.IGNORECASE | re.DOTALL),
]


@dataclass
class RejectionAnalysis:
    is_rejection: bool
    confidence: float
    rejection_reason: str
    evidence_snippet: str
    is_position_closed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_rejection": self.is_rejection,
            "confidence": round(self.confidence, 2),
            "rejection_reason": self.rejection_reason,
            "evidence_snippet": self.evidence_snippet,
            "is_position_closed": self.is_position_closed,
        }


class RejectionDetector:
    """
    Discriminates formal application rejections from generic recruitment emails or marketing blasts.
    """

    @classmethod
    def analyze_rejection(cls, subject: str, body: str) -> RejectionAnalysis:
        combined = f"{subject}\n{body}"

        for pat in _REJECTION_EVIDENCE_PATTERNS:
            m = pat.search(combined)
            if m:
                snippet = m.group(0)[:150].strip().replace("\n", " ")
                closed = "filled" in snippet.lower() or "closed" in snippet.lower() or "cancelled" in snippet.lower()
                return RejectionAnalysis(
                    is_rejection=True,
                    confidence=0.94,
                    rejection_reason="Position filled / Other candidates selected" if not closed else "Position closed / Role cancelled",
                    evidence_snippet=snippet,
                    is_position_closed=closed,
                )

        return RejectionAnalysis(
            is_rejection=False,
            confidence=0.10,
            rejection_reason="No rejection patterns detected",
            evidence_snippet="",
            is_position_closed=False,
        )
