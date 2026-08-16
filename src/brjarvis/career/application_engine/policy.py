# career/application_engine/policy.py — Platform Policy & Security Enforcement Engine
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..models import JobPosting, PlatformPolicy, PlatformPolicyState

logger = logging.getLogger("JARVIS.PlatformPolicyEngine")

KNOWN_PLATFORM_POLICIES: Dict[str, PlatformPolicy] = {
    "greenhouse": PlatformPolicy(
        platform_name="Greenhouse",
        automation_allowed=False,
        api_available=True,
        browser_allowed=True,
        manual_required=True,
        captcha_expected=False,
        policy_state=PlatformPolicyState.REVIEW_REQUIRED,
        notes="Greenhouse permits official API discovery; application submission defaults to human review.",
    ),
    "lever": PlatformPolicy(
        platform_name="Lever",
        automation_allowed=False,
        api_available=True,
        browser_allowed=True,
        manual_required=True,
        captcha_expected=False,
        policy_state=PlatformPolicyState.REVIEW_REQUIRED,
        notes="Lever public job postings supported; application submission defaults to human review.",
    ),
    "ashby": PlatformPolicy(
        platform_name="Ashby",
        automation_allowed=False,
        api_available=True,
        browser_allowed=True,
        manual_required=True,
        captcha_expected=False,
        policy_state=PlatformPolicyState.REVIEW_REQUIRED,
        notes="Ashby API discovery supported; submission defaults to human review.",
    ),
    "linkedin": PlatformPolicy(
        platform_name="LinkedIn",
        automation_allowed=False,
        api_available=False,
        browser_allowed=True,
        manual_required=True,
        captcha_expected=True,
        policy_state=PlatformPolicyState.MANUAL_REQUIRED,
        notes="Strict bot detection & CAPTCHA. Bypassing is forbidden. Manual handoff required.",
    ),
    "indeed": PlatformPolicy(
        platform_name="Indeed",
        automation_allowed=False,
        api_available=False,
        browser_allowed=True,
        manual_required=True,
        captcha_expected=True,
        policy_state=PlatformPolicyState.MANUAL_REQUIRED,
        notes="Anti-bot protection active. Manual handoff required.",
    ),
    "genericbrowser": PlatformPolicy(
        platform_name="GenericBrowser",
        automation_allowed=False,
        api_available=False,
        browser_allowed=True,
        manual_required=True,
        captcha_expected=True,
        policy_state=PlatformPolicyState.MANUAL_REQUIRED,
        notes="Unknown web forms mandate human oversight.",
    ),
}


class PlatformPolicyEngine:
    """
    Authoritative Governance Engine for Job Platforms.
    Guarantees:
    - Never bypasses CAPTCHA, Cloudflare, anti-bot mechanisms, or rate limits.
    - Fails closed to MANUAL_REQUIRED for unknown platforms.
    - Default mode is always REVIEW_BEFORE_SUBMIT.
    """

    @classmethod
    def evaluate_policy(cls, platform_name: str, job: Optional[JobPosting] = None) -> PlatformPolicy:
        """Resolve authoritative platform policy."""
        clean_name = platform_name.lower().strip().replace(" ", "").replace("_", "")
        for key, pol in KNOWN_PLATFORM_POLICIES.items():
            if key in clean_name or clean_name in key:
                return pol

        # Default fail-closed policy
        return PlatformPolicy(
            platform_name=platform_name or "UnknownPlatform",
            automation_allowed=False,
            api_available=False,
            browser_allowed=True,
            manual_required=True,
            captcha_expected=True,
            policy_state=PlatformPolicyState.MANUAL_REQUIRED,
            notes="Unknown platform: fail-closed safety policy mandates interactive manual review.",
        )

    @classmethod
    def is_submission_permitted(cls, platform_name: str) -> bool:
        """Returns True ONLY if automated submission is explicitly authorized."""
        pol = cls.evaluate_policy(platform_name)
        return pol.policy_state in (PlatformPolicyState.AUTOMATION_ALLOWED, PlatformPolicyState.API_ALLOWED)
