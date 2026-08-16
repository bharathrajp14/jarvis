# career/job_engine/finder.py — Master Job Search Orchestrator
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .adapters import (
    AshbyAdapter,
    BasePlatformAdapter,
    GenericBrowserAdapter,
    GreenhouseAdapter,
    LeverAdapter,
)
from .deduplicator import JobDeduplicator
from .matcher import JobMatcher
from .models import JobMatchResult, SearchFilters
from .ranker import JobRanker
from ..models import CareerProfile, JobPosting
from ..profile_manager import get_profile_manager
from memory.canonical_db import get_canonical_db

logger = logging.getLogger("JARVIS.JobFinder")


class JobFinder:
    """
    Master Job Search & Matching Orchestrator for BR JARVIS Career OS.
    Integrates NL query parsing, multi-adapter discovery, deduplication,
    10-factor profile matching, and ranking.
    """

    _INSTANCE: Optional[JobFinder] = None

    def __init__(self, adapters: Optional[List[BasePlatformAdapter]] = None):
        self.adapters = adapters or [
            GreenhouseAdapter(),
            LeverAdapter(),
            AshbyAdapter(),
            GenericBrowserAdapter(),
        ]
        self._init_db()

    @classmethod
    def get_instance(cls) -> JobFinder:
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def _init_db(self) -> None:
        try:
            db = get_canonical_db()
            with db.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS career_jobs (
                        job_id TEXT PRIMARY KEY,
                        company TEXT,
                        title TEXT,
                        location TEXT,
                        source TEXT,
                        platform TEXT,
                        data_json TEXT,
                        discovered_at REAL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.debug(f"Career jobs DB init note: {e}")

    # ── 1. Natural Language Query Translator ─────────────────────────────────

    @classmethod
    def parse_natural_language_query(cls, query: str, profile: Optional[CareerProfile] = None) -> SearchFilters:
        """Translate free-form user query into structured search filters."""
        low = query.lower()
        filters = SearchFilters()

        # Remote check
        if "remote" in low:
            filters.remote_only = True

        # Location checks
        locations = ["madurai", "bengaluru", "bangalore", "chennai", "hyderabad", "san francisco", "india", "us", "worldwide"]
        for loc in locations:
            if loc in low:
                filters.location = loc.capitalize()
                break

        # Roles extraction
        role_candidates = [
            ("ai engineer", ["AI Engineer", "Artificial Intelligence Engineer"]),
            ("autonomous", ["Autonomous Systems Engineer", "Autonomous Agent Architect"]),
            ("backend", ["Backend Engineer", "Senior Backend Developer"]),
            ("systems engineer", ["Systems Engineer", "Systems Architect"]),
            ("software engineer", ["Software Engineer", "Senior Software Engineer"]),
            ("python", ["Python Engineer", "Senior Python Developer"]),
            ("data scientist", ["Data Scientist", "Machine Learning Engineer"]),
            ("devops", ["DevOps Engineer", "Site Reliability Engineer"]),
            ("security", ["Cybersecurity Analyst", "Security Engineer"]),
        ]
        matched_roles = []
        for kw, roles in role_candidates:
            if kw in low:
                matched_roles.extend(roles)
        
        if matched_roles:
            filters.target_roles = list(set(matched_roles))
        elif profile and profile.preferences.target_roles:
            filters.target_roles = profile.preferences.target_roles
        else:
            filters.target_roles = ["AI Systems Engineer", "Senior Software Engineer"]

        # Keywords extraction
        filters.keywords = [w.strip() for w in low.split() if len(w.strip()) > 3 and w not in ("find", "jobs", "look", "search", "best", "give", "show", "near", "with")]
        return filters

    # ── 2. Search & Orchestrate ──────────────────────────────────────────────

    def search_and_match(
        self,
        query_or_filters: str | SearchFilters,
        profile: Optional[CareerProfile] = None,
        limit: int = 15,
    ) -> List[JobMatchResult]:
        """
        Execute full end-to-end discovery:
        NL Parse -> Multi-Adapter Query -> Deduplicate -> Match -> Rank -> Persist.
        """
        p = profile or get_profile_manager().get_profile()

        if isinstance(query_or_filters, str):
            filters = self.parse_natural_language_query(query_or_filters, profile=p)
        else:
            filters = query_or_filters

        filters.limit = limit
        all_raw_jobs: List[JobPosting] = []

        # Query all platform adapters
        for adapter in self.adapters:
            try:
                found = adapter.discover_jobs(filters)
                all_raw_jobs.extend(found)
            except Exception as e:
                logger.debug(f"Adapter '{adapter.platform_name}' discovery notice: {e}")

        # Deduplicate
        unique_jobs = JobDeduplicator.deduplicate(all_raw_jobs)

        # Match against Profile
        match_results: List[JobMatchResult] = []
        for job in unique_jobs:
            mb = JobMatcher.match(p, job)
            match_results.append(JobMatchResult(job=job, match=mb))
            # Persist job to SQLite
            self._persist_job(job)

        # Rank
        ranked = JobRanker.rank_jobs(match_results)

        logger.info(f"🎯 Job Search Complete: Discovered {len(all_raw_jobs)} -> {len(unique_jobs)} unique -> Ranked {len(ranked)} matches.")
        return ranked[:limit]

    def _persist_job(self, job: JobPosting) -> None:
        try:
            db = get_canonical_db()
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO career_jobs (job_id, company, title, location, source, platform, data_json, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.job_id,
                        job.company,
                        job.title,
                        job.location,
                        job.source,
                        job.platform,
                        json.dumps(job.to_dict()),
                        job.discovered_at,
                    )
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Job save error: {e}")

    def get_job_by_id(self, job_id: str) -> Optional[JobPosting]:
        """Fetch persisted job by ID."""
        try:
            db = get_canonical_db()
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT data_json FROM career_jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    data = json.loads(row["data_json"])
                    return JobPosting(**{k: v for k, v in data.items() if k in JobPosting.__dataclass_fields__})
        except Exception as e:
            logger.debug(f"Job fetch error: {e}")
        return None


def get_instance() -> JobFinder:
    return JobFinder.get_instance()


get_job_finder = get_instance

