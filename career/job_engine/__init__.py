# career/job_engine/__init__.py — Job Engine Subsystem Package
from __future__ import annotations

from career.job_engine.models import SearchFilters, JobMatchResult
from career.job_engine.deduplicator import JobDeduplicator
from career.job_engine.matcher import JobMatcher
from career.job_engine.ranker import JobRanker
from career.job_engine.finder import JobFinder, get_instance as get_job_finder
from career.job_engine.adapters import (
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
