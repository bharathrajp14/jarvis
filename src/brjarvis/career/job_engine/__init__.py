# career/job_engine/__init__.py — Job Engine Subsystem Package
from __future__ import annotations

from .models import SearchFilters, JobMatchResult
from .deduplicator import JobDeduplicator
from .matcher import JobMatcher
from .ranker import JobRanker
from .finder import JobFinder, get_instance as get_job_finder
from .adapters import (
    BasePlatformAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    AshbyAdapter,
    GenericBrowserAdapter,
    CompanySiteAdapter,
)

__all__ = [
    "SearchFilters",
    "JobMatchResult",
    "JobDeduplicator",
    "JobMatcher",
    "JobRanker",
    "JobFinder",
    "get_job_finder",
    "BasePlatformAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "AshbyAdapter",
    "GenericBrowserAdapter",
    "CompanySiteAdapter",
]
