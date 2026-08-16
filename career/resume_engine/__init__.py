# career/resume_engine/__init__.py — Resume Engine Subsystem Package
from __future__ import annotations

from career.resume_engine.models import (
    ResumeSchema,
    ResumeVersionRecord,
    SectionConfig,
    TemplateType,
    ThemeConfig,
)
from career.resume_engine.templates import TEMPLATES, TemplateDefinition, get_template, list_templates
from career.resume_engine.renderer import ResumeRenderer
from career.resume_engine.tailoring import ResumeTailoringEngine, ResumeDiff
from career.resume_engine.exporter import ResumeExportPipeline
from career.resume_engine.version_manager import ResumeVersionManager, get_instance as get_version_manager

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
