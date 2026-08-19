# career/analytics.py — Career Pipeline Funnel Analytics Engine
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict

from brjarvis.memory.canonical_db import get_canonical_db

from .application_engine.tracker import ApplicationTracker
from .models import ApplicationStatus

logger = logging.getLogger("JARVIS.CareerAnalytics")


@dataclass
class CareerFunnelAnalytics:
    total_jobs_discovered: int = 0
    total_matches_evaluated: int = 0
    total_shortlisted: int = 0
    total_applications_prepared: int = 0
    total_applications_submitted: int = 0
    total_screenings: int = 0
    total_interviews: int = 0
    total_technical_rounds: int = 0
    total_offers: int = 0
    total_rejected: int = 0

    # Conversion Rates (%)
    response_rate: float = 0.0  # (Screenings + Interviews + Offers) / Submitted
    interview_rate: float = 0.0  # Interviews / Submitted
    offer_rate: float = 0.0  # Offers / Interviews

    # Breakdowns
    platform_distribution: Dict[str, int] = field(default_factory=dict)
    status_counts: Dict[str, int] = field(default_factory=dict)
    variant_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    calculated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CareerAnalyticsEngine:
    """Computes transparent, evidence-based career funnel conversion telemetry."""

    @classmethod
    def compute_analytics(cls) -> CareerFunnelAnalytics:
        tracker = ApplicationTracker.get_instance()
        applications = tracker.list_applications(limit=1000)

        status_counts = tracker.get_funnel_counts()
        platform_dist: Dict[str, int] = {}
        variant_dist: Dict[str, Dict[str, Any]] = {}

        for app in applications:
            p_name = app.source_platform or "Direct"
            platform_dist[p_name] = platform_dist.get(p_name, 0) + 1

            v_id = app.resume_version_id or "master"
            if v_id not in variant_dist:
                variant_dist[v_id] = {"applications": 0, "interviews": 0, "offers": 0}
            variant_dist[v_id]["applications"] += 1
            if app.status in (ApplicationStatus.INTERVIEW, ApplicationStatus.TECHNICAL):
                variant_dist[v_id]["interviews"] += 1
            elif app.status == ApplicationStatus.OFFER:
                variant_dist[v_id]["offers"] += 1

        # Calculate discovered count from DB
        total_discovered = 0
        try:
            db = get_canonical_db()
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as cnt FROM career_jobs")
                row = cursor.fetchone()
                if row:
                    total_discovered = row["cnt"]
        except Exception:
            total_discovered = len(applications)

        submitted_cnt = (
            status_counts.get(ApplicationStatus.SUBMITTED.value, 0)
            + status_counts.get(ApplicationStatus.SUBMISSION_VERIFIED.value, 0)
            + status_counts.get(ApplicationStatus.SCREENING.value, 0)
            + status_counts.get(ApplicationStatus.INTERVIEW.value, 0)
            + status_counts.get(ApplicationStatus.TECHNICAL.value, 0)
            + status_counts.get(ApplicationStatus.OFFER.value, 0)
            + status_counts.get(ApplicationStatus.REJECTED.value, 0)
        )

        screenings_cnt = status_counts.get(ApplicationStatus.SCREENING.value, 0)
        interviews_cnt = status_counts.get(ApplicationStatus.INTERVIEW.value, 0) + status_counts.get(
            ApplicationStatus.TECHNICAL.value, 0
        )
        tech_cnt = status_counts.get(ApplicationStatus.TECHNICAL.value, 0)
        offers_cnt = status_counts.get(ApplicationStatus.OFFER.value, 0)
        rejected_cnt = status_counts.get(ApplicationStatus.REJECTED.value, 0)
        shortlisted_cnt = status_counts.get(ApplicationStatus.SHORTLISTED.value, 0)
        prepared_cnt = status_counts.get(ApplicationStatus.PREPARING.value, 0) + status_counts.get(
            ApplicationStatus.READY_FOR_REVIEW.value, 0
        )

        # Rates
        responses_cnt = screenings_cnt + interviews_cnt + offers_cnt + rejected_cnt
        resp_rate = round((responses_cnt / max(1, submitted_cnt)) * 100.0, 1) if submitted_cnt > 0 else 0.0
        int_rate = round((interviews_cnt / max(1, submitted_cnt)) * 100.0, 1) if submitted_cnt > 0 else 0.0
        off_rate = round((offers_cnt / max(1, interviews_cnt)) * 100.0, 1) if interviews_cnt > 0 else 0.0

        return CareerFunnelAnalytics(
            total_jobs_discovered=total_discovered,
            total_matches_evaluated=total_discovered,
            total_shortlisted=shortlisted_cnt,
            total_applications_prepared=prepared_cnt,
            total_applications_submitted=submitted_cnt,
            total_screenings=screenings_cnt,
            total_interviews=interviews_cnt,
            total_technical_rounds=tech_cnt,
            total_offers=offers_cnt,
            total_rejected=rejected_cnt,
            response_rate=resp_rate,
            interview_rate=int_rate,
            offer_rate=off_rate,
            platform_distribution=platform_dist,
            status_counts=status_counts,
            variant_performance=variant_dist,
            calculated_at=time.time(),
        )
