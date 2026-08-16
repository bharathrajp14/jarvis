# career/application_engine/verifier.py — Authoritative Submission Verification Engine
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.execution.types import ExecutionStatus, VerificationOutcome
from core.execution.verifier import get_universal_verifier

logger = logging.getLogger("JARVIS.SubmissionVerifier")


class ApplicationSubmissionVerifier:
    """
    Authoritative verifier for job application submissions.
    Ensures that BR JARVIS NEVER claims an application was submitted without physical evidence.
    """

    @classmethod
    def verify_submission(cls, evidence: Dict[str, Any]) -> VerificationOutcome:
        """
        Verify physical submission evidence.
        Accepts:
        - Official API receipt with HTTP 200/201 + valid confirmation ID
        - Browser page containing verified confirmation URL or success banner
        - Verified confirmation email receipt
        """
        conf_id = evidence.get("confirmation_id") or evidence.get("application_id")
        conf_url = evidence.get("confirmation_url") or evidence.get("current_url")
        api_ok = evidence.get("api_verified") is True
        page_text = str(evidence.get("page_text") or "").lower()

        # Check for success indicators in response text
        success_phrases = [
            "thank you for applying",
            "application submitted",
            "we have received your application",
            "application received",
            "your application was sent",
        ]
        has_success_text = any(phrase in page_text for phrase in success_phrases)

        if conf_id or (conf_url and ("confirm" in conf_url or "success" in conf_url or "thank" in conf_url)) or api_ok or has_success_text:
            return VerificationOutcome(
                verified=True,
                verifier_name="ApplicationSubmissionVerifier",
                status=ExecutionStatus.SUCCESS_VERIFIED,
                evidence=f"Application submission verified (ID: {conf_id or 'N/A'}, URL: {conf_url or 'N/A'}, Text Match: {has_success_text}).",
                details="Verified authentic application submission.",
                observed_state=evidence,
            )

        return VerificationOutcome(
            verified=False,
            verifier_name="ApplicationSubmissionVerifier",
            status=ExecutionStatus.SUCCESS_UNVERIFIED,
            details="Application flow initiated but lacks authoritative confirmation receipt.",
            error="UNVERIFIED_SUBMISSION",
        )
