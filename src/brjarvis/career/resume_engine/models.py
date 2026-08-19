# career/resume_engine/models.py — Resume Schemas, Themes, and Variants
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TemplateType(str, Enum):
    EXECUTIVE = "executive"
    MODERN_MINIMAL = "modern_minimal"
    ATS_CLASSIC = "ats_classic"
    TECHNICAL_ENGINEER = "technical_engineer"
    DEVELOPER = "developer"
    FRESH_GRADUATE = "fresh_graduate"
    STARTUP_PRODUCT = "startup_product"
    AI_DATA = "ai_data"
    CYBERSECURITY = "cybersecurity"
    COMPACT_ONE_PAGE = "compact_one_page"


@dataclass
class ThemeConfig:
    theme_id: str = "navy_slate"
    name: str = "Navy Slate"
    primary_color: str = "#1B365D"  # Deep Navy / Header / Primary Accents
    secondary_color: str = "#4B6B94"  # Slate Blue / Subtitles
    accent_color: str = "#00A896"  # Teal Accent / Badges / Lines
    text_color: str = "#1A202C"  # Dark Charcoal / Body
    muted_text: str = "#718096"  # Muted Gray / Dates / Locations
    background_color: str = "#FFFFFF"  # Paper White
    card_background: str = "#F7FAFC"  # Subtle Card Gray
    font_heading: str = "Inter, sans-serif"
    font_body: str = "Inter, sans-serif"
    font_code: str = "'Share Tech Mono', monospace"
    font_size_base: str = "10.5pt"
    line_height: str = "1.45"
    margin_pt: int = 36  # 0.5 inch margins default
    border_radius: str = "4px"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SectionConfig:
    section_id: str  # "summary", "experience", "education", "skills", "projects", "certifications", "achievements"
    title: str
    visible: bool = True
    order: int = 1
    layout: str = "standard"  # "standard", "dual_column", "grid", "pills", "compact"
    custom_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResumeSchema:
    """Canonical View Model representing a rendered/customized Resume."""

    resume_id: str = field(default_factory=lambda: f"res_{uuid.uuid4().hex[:8]}")
    title: str = "Master Resume"
    target_role: str = "Autonomous AI Systems Architect"
    template_id: TemplateType = TemplateType.ATS_CLASSIC
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    sections: List[SectionConfig] = field(default_factory=list)

    # Rendered content snapshot derived from CareerProfile
    full_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    location: str = ""
    links: Dict[str, str] = field(default_factory=dict)
    summary: str = ""
    experience: List[Dict[str, Any]] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[Dict[str, Any]] = field(default_factory=list)
    achievements: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    is_master: bool = False
    parent_version_id: Optional[str] = None
    job_id_targeted: Optional[str] = None
    ats_score: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["template_id"] = (
            self.template_id.value if isinstance(self.template_id, TemplateType) else str(self.template_id)
        )
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResumeSchema:
        d = dict(data)
        tmpl = d.get("template_id", "ats_classic")
        try:
            d["template_id"] = TemplateType(tmpl)
        except Exception:
            d["template_id"] = TemplateType.ATS_CLASSIC

        if "theme" in d and isinstance(d["theme"], dict):
            d["theme"] = ThemeConfig(**{k: v for k, v in d["theme"].items() if k in ThemeConfig.__dataclass_fields__})
        if "sections" in d and isinstance(d["sections"], list):
            d["sections"] = [
                SectionConfig(**{k: v for k, v in s.items() if k in SectionConfig.__dataclass_fields__})
                if isinstance(s, dict)
                else s
                for s in d["sections"]
            ]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ResumeVersionRecord:
    version_id: str
    resume_id: str
    title: str
    template_id: str
    target_role: str
    job_id: Optional[str] = None
    ats_score: float = 0.0
    provider: str = "native"  # "native" or "canva"
    canva_design_id: Optional[str] = None
    canva_edit_url: Optional[str] = None
    docx_path: Optional[str] = None
    pdf_path: Optional[str] = None
    html_path: Optional[str] = None
    source_hash: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
