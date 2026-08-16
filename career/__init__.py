# career/__init__.py — Master Package for BR JARVIS Career OS
from __future__ import annotations

from career.models import (
    CareerProfile,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    SkillCategory,
    WorkPreferences,
    SalaryPreferences,
    JobPosting,
    MatchBreakdown,
    ApplicationStatus,
    PlatformPolicy,
    ApplicationPackage,
    ApplicationRecord,
)
from career.profile_manager import CareerProfileManager, get_profile_manager
from career.resume_engine import (
    ResumeSchema,
    ResumeRenderer,
    ResumeTailoringEngine,
    ResumeExportPipeline,
    ResumeVersionManager,
    TemplateType,
    list_templates,
)
from career.ats_engine import ATSEngine, ATSScoreReport
from career.cover_letter import CoverLetterGenerator
from career.job_engine import JobFinder, JobMatcher, JobRanker, SearchFilters
from career.application_engine import (
    ApplicationTracker,
    ManualApplicationAssistant,
    ApplicationPackageBuilder,
    PlatformPolicyEngine,
    DuplicateApplicationGuard,
)
from career.analytics import CareerAnalyticsEngine
from career.interview_prep import InterviewPrepGenerator
from career.canva import CanvaAdapter, CanvaCapabilityProbe
from career.api_routes import router as career_api_router

# Ensure dynamic tools are registered upon module load
import career.tools  # noqa: F401

__all__ = [
    "CareerProfile",
    "EducationEntry",
    "ExperienceEntry",
    "ProjectEntry",
    "SkillCategory",
    "WorkPreferences",
    "SalaryPreferences",
    "JobPosting",
    "MatchBreakdown",
    "ApplicationStatus",
    "PlatformPolicy",
    "ApplicationPackage",
    "ApplicationRecord",
    "CareerProfileManager",
    "get_profile_manager",
    "ResumeSchema",
    "ResumeRenderer",
    "ResumeTailoringEngine",
    "ResumeExportPipeline",
    "ResumeVersionManager",
    "TemplateType",
    "list_templates",
    "ATSEngine",
    "ATSScoreReport",
    "CoverLetterGenerator",
    "JobFinder",
    "JobMatcher",
    "JobRanker",
    "SearchFilters",
    "ApplicationTracker",
    "ManualApplicationAssistant",
    "ApplicationPackageBuilder",
    "PlatformPolicyEngine",
    "DuplicateApplicationGuard",
    "CareerAnalyticsEngine",
    "InterviewPrepGenerator",
    "CanvaAdapter",
    "CanvaCapabilityProbe",
    "career_api_router",
]
