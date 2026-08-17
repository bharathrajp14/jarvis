# career/memory_integration.py — UnifiedMemory Synchronization for Career OS
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .models import CareerProfile, ApplicationRecord

logger = logging.getLogger("JARVIS.CareerMemory")


def sync_profile_to_memory(profile: CareerProfile) -> None:
    """
    Synchronize verified career facts and preferences into UnifiedMemory.
    Stores structured facts in L4 Persistent Memory and vectors in L3.
    """
    try:
        from brjarvis.memory.unified_memory import UnifiedMemoryManager
        from brjarvis.core.runtime import get_runtime

        runtime = get_runtime()
        mem_mgr: Optional[UnifiedMemoryManager] = None
        try:
            mem_mgr = runtime.container.resolve(UnifiedMemoryManager)
        except Exception:
            mem_mgr = UnifiedMemoryManager()

        if not mem_mgr:
            return

        # 1. Store Target Roles & Work Preferences
        roles_str = ", ".join(profile.preferences.target_roles)
        mem_mgr.remember(
            name="career_target_roles",
            content=f"Candidate Target Roles: {roles_str}. Work Mode: {profile.preferences.remote_preference}. Locations: {', '.join(profile.preferences.target_locations)}",
            description="Active career target preferences and locations",
            mem_type="career_preference",
            scope="user",
        )

        # 2. Store Core Technical Competencies
        for sc in profile.skills:
            cat_name = sc.category.lower().replace(" ", "_")
            mem_mgr.remember(
                name=f"career_skills_{cat_name}",
                content=f"{sc.category}: {', '.join(sc.skills)}",
                description=f"Verified technical competencies in {sc.category}",
                mem_type="career_skill",
                scope="user",
            )

        # 3. Store Executive Summary
        if profile.summary:
            mem_mgr.remember(
                name="career_executive_summary",
                content=profile.summary,
                description="Master career executive summary",
                mem_type="career_summary",
                scope="user",
            )

        logger.info("🧠 Career Profile synchronized with UnifiedMemory (L3/L4).")
    except Exception as e:
        logger.debug(f"Memory synchronization note: {e}")


def sync_application_to_memory(app: ApplicationRecord) -> None:
    """Record verified application outcome in UnifiedMemory."""
    try:
        from brjarvis.memory.unified_memory import UnifiedMemoryManager
        mem_mgr = UnifiedMemoryManager()

        status_val = app.application_status.value if hasattr(app.application_status, "value") else str(app.application_status)
        mem_mgr.remember(
            name=f"job_app_{app.company.lower().replace(' ', '_')}_{app.application_id.lower()}",
            content=f"Applied for {app.job_title} at {app.company} via {app.platform}. Status: {status_val}. Date: {app.date_applied or 'N/A'}",
            description=f"Career application record for {app.company}",
            mem_type="job_application",
            scope="user",
        )
    except Exception as e:
        logger.debug("Application memory sync note: %s", e)


def sync_career_memory(event_type: str, application: Optional[ApplicationRecord] = None, payload: Optional[Dict[str, Any]] = None) -> None:
    """
    Ingest discrete career milestone into UnifiedMemory L4 store.
    """
    try:
        from brjarvis.memory.unified_memory import UnifiedMemoryManager
        mem_mgr = UnifiedMemoryManager()

        app_info = f" ({application.company} — {application.job_title})" if application else ""
        content = f"Career Milestone: {event_type}{app_info} at {json.dumps(payload or {})}"

        mem_mgr.remember(
            name=f"career_event_{int(time.time()*1000)}",
            content=content,
            description=f"Career Event: {event_type}",
            mem_type="career_event",
            scope="user",
        )
    except Exception as exc:
        logger.debug("Event memory sync note: %s", exc)


def analyze_career_learning() -> Dict[str, Any]:
    """
    Analyze historical application performance to infer evidence-backed career insights.
    Compares response and interview conversion rates across resume variants and job platforms.
    """
    from brjarvis.career.crm.database import get_career_crm_db
    db = get_career_crm_db()
    apps = db.list_applications(limit=1000)

    resume_stats: Dict[str, Dict[str, int]] = {}
    source_stats: Dict[str, Dict[str, int]] = {}

    for a in apps:
        rv = a.resume_version or "master"
        src = a.platform or "Direct"

        if rv not in resume_stats:
            resume_stats[rv] = {"applications": 0, "responses": 0, "interviews": 0, "offers": 0}
        if src not in source_stats:
            source_stats[src] = {"applications": 0, "responses": 0, "interviews": 0, "offers": 0}

        resume_stats[rv]["applications"] += 1
        source_stats[src]["applications"] += 1

        st = a.application_status.value if hasattr(a.application_status, "value") else str(a.application_status)
        if st in ("SCREENING", "INTERVIEW_REQUESTED", "INTERVIEW_SCHEDULED", "TECHNICAL_ROUND", "FINAL_ROUND", "OFFER_RECEIVED", "OFFER_ACCEPTED", "REJECTED"):
            resume_stats[rv]["responses"] += 1
            source_stats[src]["responses"] += 1
        if st in ("INTERVIEW_REQUESTED", "INTERVIEW_SCHEDULED", "TECHNICAL_ROUND", "FINAL_ROUND", "OFFER_RECEIVED", "OFFER_ACCEPTED"):
            resume_stats[rv]["interviews"] += 1
            source_stats[src]["interviews"] += 1
        if st in ("OFFER_RECEIVED", "OFFER_ACCEPTED"):
            resume_stats[rv]["offers"] += 1
            source_stats[src]["offers"] += 1

    insights: List[str] = []
    # Identify top performing resume variant if sample size >= 3
    for rv, data in resume_stats.items():
        if data["applications"] >= 3:
            int_rate = (data["interviews"] / data["applications"]) * 100
            insights.append(f"Resume variant '{rv}' observed {int_rate:.1f}% interview conversion across {data['applications']} applications.")

    # Identify top performing source
    for src, data in source_stats.items():
        if data["applications"] >= 3:
            resp_rate = (data["responses"] / data["applications"]) * 100
            insights.append(f"Job source '{src}' produced {resp_rate:.1f}% response rate across {data['applications']} applications.")

    return {
        "resume_performance": resume_stats,
        "source_performance": source_stats,
        "insights": insights,
        "sample_size": len(apps),
    }

