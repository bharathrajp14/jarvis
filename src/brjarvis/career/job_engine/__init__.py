# career/job_engine/__init__.py — Job Engine Subsystem Package
from __future__ import annotations

from .adapters import (
    AshbyAdapter,
    BasePlatformAdapter,
    CompanySiteAdapter,
    GenericBrowserAdapter,
    GreenhouseAdapter,
    LeverAdapter,
)
from .deduplicator import JobDeduplicator
from .finder import JobFinder
from .finder import get_instance as get_job_finder
from .matcher import JobMatcher
from .models import JobMatchResult, SearchFilters
from .ranker import JobRanker

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
