# career/__init__.py — Master Package for BR JARVIS Career OS
from __future__ import annotations

import sys

# Ensure dynamic tools are registered upon module load
from . import tools  # noqa: F401
from .analytics import CareerAnalyticsEngine
from .api_routes import router as career_api_router
from .application_engine import (
    ApplicationPackageBuilder,
    ApplicationTracker,
    DuplicateApplicationGuard,
    ManualApplicationAssistant,
    PlatformPolicyEngine,
)
from .ats_engine import ATSEngine, ATSScoreReport
from .canva import CanvaAdapter, CanvaCapabilityProbe
from .cover_letter import CoverLetterGenerator
from .interview_prep import InterviewPrepGenerator
from .job_engine import JobFinder, JobMatcher, JobRanker, SearchFilters
from .models import (
    ApplicationPackage,
    ApplicationRecord,
    ApplicationStatus,
    CareerProfile,
    EducationEntry,
    ExperienceEntry,
    JobPosting,
    MatchBreakdown,
    PlatformPolicy,
    ProjectEntry,
    SalaryPreferences,
    SkillCategory,
    WorkPreferences,
)
from .profile_manager import CareerProfileManager, get_profile_manager
from .resume_engine import (
    ResumeExportPipeline,
    ResumeRenderer,
    ResumeSchema,
    ResumeTailoringEngine,
    ResumeVersionManager,
    TemplateType,
    list_templates,
)

# Mark career tools as loaded in registry guard so it won't double-import
try:
    from brjarvis.tools.registry import _loaded_plugins

    _loaded_plugins.add("career.tools")
    _loaded_plugins.add("brjarvis.career.tools")
except Exception:
    pass

# Register legacy aliases AFTER all imports are complete
if __name__ in sys.modules:
    sys.modules.setdefault("career", sys.modules[__name__])

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
