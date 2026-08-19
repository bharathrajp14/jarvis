# career/job_engine/deduplicator.py — Multi-Key Job Deduplication Engine
from __future__ import annotations

import hashlib
import logging
import re
from typing import List, Set

from ..models import JobPosting

logger = logging.getLogger("JARVIS.JobDeduplicator")


class JobDeduplicator:
    """
    Robust multi-key deduplicator for job postings.
    Prevents repeated entries from multiple feeds, aggregators, and search hits.
    """

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Strip tracking query parameters (utm_source, ref, gh_src, etc.)."""
        base = url.split("?")[0].rstrip("/").lower()
        return base

    @classmethod
    def normalize_str(cls, text: str) -> str:
        """Normalize string removing punctuation and extra whitespace."""
        return re.sub(r"[^\w\s]", "", text.lower()).strip()

    @classmethod
    def compute_signature(cls, job: JobPosting) -> str:
        """Generate canonical composite hash signature."""
        comp = cls.normalize_str(job.company)
        title = cls.normalize_str(job.title)
        loc = cls.normalize_str(job.location)
        sig_str = f"{comp}|{title}|{loc}"
        return hashlib.sha256(sig_str.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def deduplicate(cls, jobs: List[JobPosting]) -> List[JobPosting]:
        """Filter out duplicates using multi-key hashes."""
        seen_ids: Set[str] = set()
        seen_urls: Set[str] = set()
        seen_signatures: Set[str] = set()
        unique_jobs: List[JobPosting] = []

        for job in jobs:
            if not job.job_id or not job.title:
                continue

            # Check Key 1: job_id
            if job.job_id in seen_ids:
                continue

            # Check Key 2: application URL
            if job.application_url:
                clean_u = cls.clean_url(job.application_url)
                if clean_u in seen_urls:
                    continue
                seen_urls.add(clean_u)

            # Check Key 3: Composite signature
            sig = cls.compute_signature(job)
            if sig in seen_signatures:
                continue

            seen_ids.add(job.job_id)
            seen_signatures.add(sig)
            unique_jobs.append(job)

        dedup_count = len(jobs) - len(unique_jobs)
        if dedup_count > 0:
            logger.info(f"🧹 Deduplicated {dedup_count} redundant job postings ({len(unique_jobs)} unique remaining)")

        return unique_jobs
