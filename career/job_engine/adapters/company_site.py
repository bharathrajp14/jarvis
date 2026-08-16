# career/job_engine/adapters/company_site.py — Generic Company Career Portal Adapter
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from career.job_engine.adapters.base import BasePlatformAdapter
from career.job_engine.models import SearchFilters
from career.models import (
    ApplicationQuestion,
    JobPosting,
    PlatformPolicy,
    PlatformPolicyState,
)

logger = logging.getLogger("JARVIS.CompanySiteAdapter")


class CompanySiteAdapter(BasePlatformAdapter):
    """
    Adapter for direct company website job portals.
    Defaults to manual submission review.
    """

    @property
    def platform_name(self) -> str:
        return "CompanyCareerPortal"

    @property
    def policy(self) -> PlatformPolicy:
        return PlatformPolicy(
            platform_name="CompanyCareerPortal",
            automation_allowed=False,
            api_available=False,
            browser_allowed=True,
            manual_required=True,
            captcha_expected=True,
            policy_state=PlatformPolicyState.MANUAL_REQUIRED,
            notes="Company portal parsing with manual application handoff.",
        )

    def discover_jobs(self, filters: SearchFilters) -> List[JobPosting]:
        return []

    def get_job_details(self, job_id: str, url: Optional[str] = None) -> Optional[JobPosting]:
        return None

    def get_application_questions(self, job: JobPosting) -> List[ApplicationQuestion]:
        return [
            ApplicationQuestion(
                question_id="full_name",
                question_text="Full Name",
                field_type="text",
                required=True,
                suggested_answer="Bharath Raj",
            ),
            ApplicationQuestion(
                question_id="email",
                question_text="Email",
                field_type="text",
                required=True,
                suggested_answer="bharthraj1412@gmail.com",
            ),
        ]
