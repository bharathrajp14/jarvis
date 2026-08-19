# career/job_engine/models.py — Job Engine Models & Filters
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from ..models import JobPosting, MatchBreakdown


@dataclass
class SearchFilters:
    keywords: List[str] = field(default_factory=list)
    target_roles: List[str] = field(default_factory=list)
    location: str = ""
    remote_only: bool = False
    hybrid_allowed: bool = True
    employment_types: List[str] = field(default_factory=lambda: ["Full-time"])
    min_salary: float = 0.0
    companies: List[str] = field(default_factory=list)
    excluded_companies: List[str] = field(default_factory=list)
    posted_within_days: int = 30
    limit: int = 25

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobMatchResult:
    job: JobPosting
    match: MatchBreakdown
    ranked_score: float = 0.0
    is_shortlisted: bool = False
    is_applied: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "match": self.match.to_dict(),
            "ranked_score": self.ranked_score,
            "is_shortlisted": self.is_shortlisted,
            "is_applied": self.is_applied,
            "created_at": self.created_at,
        }
