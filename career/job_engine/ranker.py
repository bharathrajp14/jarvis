# career/job_engine/ranker.py — Quality-First Job Ranking Engine
from __future__ import annotations

import logging
from typing import List

from career.job_engine.models import JobMatchResult

logger = logging.getLogger("JARVIS.JobRanker")


class JobRanker:
    """
    Ranks job postings prioritizing long-term career growth, skill relevance,
    compensation transparency, and company reputation over raw job count.
    """

    @classmethod
    def rank_jobs(cls, match_results: List[JobMatchResult]) -> List[JobMatchResult]:
        """Rank job match results by composite quality score."""
        for res in match_results:
            job = res.job
            match = res.match

            score = match.overall_score

            # Boost for explicit transparent salary
            if job.salary and any(c.isdigit() for c in job.salary):
                score += 5.0

            # Boost for direct remote compatibility
            if "remote" in job.remote_type.lower():
                score += 4.0

            # Boost for official API application method (smoother experience)
            if job.application_method == "official_api":
                score += 3.0

            # Cap at 100.0
            res.ranked_score = round(min(100.0, score), 1)

        # Sort descending by ranked_score
        ranked = sorted(match_results, key=lambda x: x.ranked_score, reverse=True)
        return ranked
