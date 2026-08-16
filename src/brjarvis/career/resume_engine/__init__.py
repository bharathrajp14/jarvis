# career/resume_engine/__init__.py — Resume Engine Subsystem Package
from __future__ import annotations

import sys
_mod = sys.modules.get(__name__)
if _mod:
    sys.modules["career.resume_engine"] = _mod
    sys.modules["brjarvis.career.resume_engine"] = _mod

from .models import (
    ResumeSchema,
    ResumeVersionRecord,
    SectionConfig,
    TemplateType,
    ThemeConfig,
)
from .templates import TEMPLATES, TemplateDefinition, get_template, list_templates
from .renderer import ResumeRenderer
from .tailoring import ResumeTailoringEngine, ResumeDiff
from .exporter import ResumeExportPipeline
from .version_manager import ResumeVersionManager, get_instance as get_version_manager

__all__ = [
    "TemplateType",
    "ThemeConfig",
    "SectionConfig",
    "ResumeSchema",
    "ResumeVersionRecord",
    "TemplateDefinition",
    "TEMPLATES",
    "get_template",
    "list_templates",
    "ResumeRenderer",
    "ResumeTailoringEngine",
    "ResumeDiff",
    "ResumeExportPipeline",
    "ResumeVersionManager",
    "get_version_manager",
]
