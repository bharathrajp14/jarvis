# career/__init__.py — Master Package for BR JARVIS Career OS
from __future__ import annotations

import sys

from .models import (
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
from .profile_manager import CareerProfileManager, get_profile_manager
from .resume_engine import (
    ResumeSchema,
    ResumeRenderer,
    ResumeTailoringEngine,
    ResumeExportPipeline,
    ResumeVersionManager,
    TemplateType,
    list_templates,
)
from .ats_engine import ATSEngine, ATSScoreReport
from .cover_letter import CoverLetterGenerator
from .job_engine import JobFinder, JobMatcher, JobRanker, SearchFilters
from .application_engine import (
    ApplicationTracker,
    ManualApplicationAssistant,
    ApplicationPackageBuilder,
    PlatformPolicyEngine,
    DuplicateApplicationGuard,
)
from .analytics import CareerAnalyticsEngine
from .interview_prep import InterviewPrepGenerator
from .canva import CanvaAdapter, CanvaCapabilityProbe
from .api_routes import router as career_api_router

# Ensure dynamic tools are registered upon module load
from . import tools  # noqa: F401
# Mark career tools as loaded in registry guard so it won't double-import
try:
    from brjarvis.tools.registry import _loaded_plugins
    _loaded_plugins.add("career.tools")
    _loaded_plugins.add("brjarvis.career.tools")
except Exception:
    pass

# Register legacy aliases AFTER all imports are complete (avoids partially-initialized module)
_self = sys.modules[__name__]
sys.modules.setdefault("career", _self)
sys.modules["brjarvis.career"] = _self

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
