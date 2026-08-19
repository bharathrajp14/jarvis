# career/job_engine/matcher.py — 10-Factor Transparent Job Matcher
from __future__ import annotations

import logging
from typing import Set

from ..models import CareerProfile, JobPosting, MatchBreakdown
from ..resume_engine.tailoring import ResumeTailoringEngine

logger = logging.getLogger("JARVIS.JobMatcher")


class JobMatcher:
    """
    Transparent multi-factor job matching and scoring engine.
    Calculates granular sub-scores across 10 dimensions and generates a clear explanation.
    """

    @classmethod
    def match(cls, profile: CareerProfile, job: JobPosting) -> MatchBreakdown:
        """Compute transparent multi-factor fit between CareerProfile and JobPosting."""
        jd_text = f"{job.title} {job.description} {' '.join(job.requirements)} {' '.join(job.technologies)}".lower()
        jd_tokens = ResumeTailoringEngine.extract_keywords(jd_text)

        # 1. Skills Match (30% Weight)
        candidate_skills: Set[str] = set()
        for cat in profile.skills:
            for s in cat.skills:
                candidate_skills.add(s.lower().split("(")[0].strip())

        matched_skills = []
        missing_skills = []
        for tech in job.technologies:
            tech_clean = tech.lower().strip()
            if any(tech_clean in cs or cs in tech_clean for cs in candidate_skills):
                matched_skills.append(tech)
            else:
                missing_skills.append(tech)

        for req in job.requirements:
            req_tokens = ResumeTailoringEngine.extract_keywords(req)
            for rt in req_tokens:
                if any(rt in cs for cs in candidate_skills):
                    if rt.title() not in matched_skills:
                        matched_skills.append(rt.title())
                else:
                    if rt.title() not in missing_skills and rt.title() not in matched_skills and len(rt) > 3:
                        missing_skills.append(rt.title())

        skills_score = (
            min(100.0, (len(matched_skills) / max(1, len(matched_skills) + len(missing_skills))) * 120.0)
            if (matched_skills or missing_skills)
            else 85.0
        )

        # 2. Experience & Seniority Fit (20% Weight)
        exp_score = 90.0
        exp_years = len(profile.experience) * 1.5  # Approximate
        if "senior" in job.title.lower() or "lead" in job.title.lower() or "staff" in job.title.lower():
            if exp_years >= 3.0:
                exp_score = 95.0
            else:
                exp_score = 75.0
        elif "junior" in job.title.lower() or "entry" in job.title.lower():
            exp_score = 95.0

        # 3. Education Fit (10% Weight)
        edu_score = 90.0
        if profile.education:
            edu_score = (
                100.0
                if any(
                    "bachelor" in e.degree.lower() or "master" in e.degree.lower() or "b.e." in e.degree.lower()
                    for e in profile.education
                )
                else 85.0
            )

        # 4. Location & Remote Policy Fit (15% Weight)
        loc_score = 80.0
        pref_remote = profile.preferences.remote_preference.lower()
        job_remote = job.remote_type.lower()

        if "remote" in job_remote or "remote" in job.location.lower():
            loc_score = 100.0
        elif any(loc.lower() in job.location.lower() for loc in profile.preferences.target_locations):
            loc_score = 95.0
        elif pref_remote == "remote_only" and "onsite" in job_remote:
            loc_score = 45.0
        else:
            loc_score = 75.0

        # 5. Role & Title Affinity (15% Weight)
        role_score = 70.0
        target_roles = [r.lower() for r in profile.preferences.target_roles]
        j_title = job.title.lower()

        if any(tr in j_title or j_title in tr for tr in target_roles):
            role_score = 98.0
        elif any(part in j_title for tr in target_roles for part in tr.split() if len(part) > 3):
            role_score = 85.0

        # 6. Company Preferences (10% Weight)
        comp_score = 85.0
        c_name = job.company.lower()
        if any(exc.lower() in c_name for exc in profile.preferences.excluded_companies):
            comp_score = 0.0
        elif any(pref.lower() in c_name for pref in profile.preferences.preferred_companies):
            comp_score = 100.0

        # Weighted Overall Score
        overall = (
            (skills_score * 0.30)
            + (exp_score * 0.20)
            + (edu_score * 0.10)
            + (loc_score * 0.15)
            + (role_score * 0.15)
            + (comp_score * 0.10)
        )
        overall = round(max(0.0, min(100.0, overall)), 1)

        # Generate Strengths & Weaknesses
        strengths = []
        if skills_score >= 85.0:
            strengths.append(f"Strong technical alignment ({len(matched_skills)} core competencies matched).")
        if loc_score >= 95.0:
            strengths.append("Perfect work mode / location compatibility.")
        if role_score >= 85.0:
            strengths.append(f"Target role title aligns directly with '{job.title}'.")
        if exp_score >= 90.0:
            strengths.append("Demonstrated professional background meets seniority requirements.")

        weaknesses = []
        if missing_skills:
            weaknesses.append(f"Job mentions keywords not highlighted in profile: {', '.join(missing_skills[:4])}.")
        if loc_score < 70.0:
            weaknesses.append(f"Location '{job.location}' requires onsite/hybrid commute outside primary target.")

        explanation = (
            f"Overall Match: {overall}%. Skills fit is {skills_score:.0f}% with {len(matched_skills)} direct keyword alignments. "
            f"Role affinity is {role_score:.0f}% and location compatibility is {loc_score:.0f}%."
        )

        return MatchBreakdown(
            overall_score=overall,
            skills_score=round(skills_score, 1),
            experience_score=round(exp_score, 1),
            education_score=round(edu_score, 1),
            location_score=round(loc_score, 1),
            role_fit_score=round(role_score, 1),
            matched_skills=matched_skills[:15],
            missing_skills=missing_skills[:8],
            key_strengths=strengths,
            weak_areas=weaknesses,
            fit_explanation=explanation,
        )
