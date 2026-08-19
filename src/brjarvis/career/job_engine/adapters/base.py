# career/job_engine/adapters/base.py — Base Platform Adapter Contract
from __future__ import annotations

import abc
import time
from typing import Any, Dict, List, Optional

from ...models import ApplicationPackage, ApplicationQuestion, JobPosting, PlatformPolicy, PlatformPolicyState
from ..models import SearchFilters


class BasePlatformAdapter(abc.ABC):
    """
    Standard interface for all job discovery and application platform adapters.
    Each adapter must truthfully declare its operational capabilities and policies.
    """

    @property
    @abc.abstractmethod
    def platform_name(self) -> str:
        """Name of the platform (e.g., 'Greenhouse', 'Lever', 'Ashby', 'GenericBrowser')."""
        pass

    @property
    @abc.abstractmethod
    def policy(self) -> PlatformPolicy:
        """Declared platform automation policy."""
        pass

    @abc.abstractmethod
    def discover_jobs(self, filters: SearchFilters) -> List[JobPosting]:
        """Discover and return normalized job postings matching filters."""
        pass

    @abc.abstractmethod
    def get_job_details(self, job_id: str, url: Optional[str] = None) -> Optional[JobPosting]:
        """Fetch full job requirements and metadata."""
        pass

    @abc.abstractmethod
    def get_application_questions(self, job: JobPosting) -> List[ApplicationQuestion]:
        """Extract application form questions and field constraints."""
        pass

    def prepare_application_data(
        self, job: JobPosting, answers: Dict[str, Any], package: ApplicationPackage
    ) -> Dict[str, Any]:
        """Format application payload suitable for submission or form-filling."""
        return {
            "job_id": job.job_id,
            "platform": self.platform_name,
            "answers": answers,
            "package_id": package.package_id,
            "resume_path": package.resume_pdf_path or package.resume_docx_path,
            "prepared_at": time.time(),
        }

    def submit_application(self, job: JobPosting, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt submission if explicitly permitted by policy and authorized by user.
        Default implementation fails closed to manual review.
        """
        if (
            self.policy.policy_state != PlatformPolicyState.AUTOMATION_ALLOWED
            and self.policy.policy_state != PlatformPolicyState.API_ALLOWED
        ):
            return {
                "success": False,
                "status": "MANUAL_REQUIRED",
                "message": f"Platform '{self.platform_name}' requires human manual submission.",
                "policy": self.policy.to_dict(),
            }
        return {
            "success": False,
            "status": "MANUAL_ACTION_REQUIRED",
            "message": "Submission requires interactive human confirmation.",
        }
