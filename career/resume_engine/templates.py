# career/resume_engine/templates.py — 10 Native Production Resume Templates for BR JARVIS
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from career.models import CareerProfile
from career.resume_engine.models import ResumeSchema, SectionConfig, TemplateType, ThemeConfig


@dataclass
class TemplateDefinition:
    template_id: TemplateType
    name: str
    description: str
    category: str
    ats_friendly: bool
    recommended_for: List[str]
    default_theme: ThemeConfig
    default_sections: List[SectionConfig]
    css_template: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id.value,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "ats_friendly": self.ats_friendly,
            "recommended_for": self.recommended_for,
            "default_theme": self.default_theme.to_dict(),
            "default_sections": [s.to_dict() for s in self.default_sections],
        }


# ── Common Default Section Configs ───────────────────────────────────────────

def _standard_sections() -> List[SectionConfig]:
    return [
        SectionConfig(section_id="summary", title="Professional Summary", visible=True, order=1, layout="standard"),
        SectionConfig(section_id="skills", title="Core Technical Competencies", visible=True, order=2, layout="pills"),
        SectionConfig(section_id="experience", title="Professional Experience", visible=True, order=3, layout="standard"),
        SectionConfig(section_id="projects", title="Featured Engineering Projects", visible=True, order=4, layout="standard"),
        SectionConfig(section_id="education", title="Education & Academic Background", visible=True, order=5, layout="standard"),
        SectionConfig(section_id="certifications", title="Certifications & Credentials", visible=True, order=6, layout="standard"),
        SectionConfig(section_id="achievements", title="Honors & Achievements", visible=True, order=7, layout="standard"),
    ]


# ── 10 Native Production Templates ───────────────────────────────────────────

TEMPLATES: Dict[TemplateType, TemplateDefinition] = {
    # 1. Executive
    TemplateType.EXECUTIVE: TemplateDefinition(
        template_id=TemplateType.EXECUTIVE,
        name="Executive Leadership",
        description="Prestigious navy & slate serif/sans-serif styling designed for Directors, VPs, Principal Architects, and Engineering Leaders.",
        category="Leadership",
        ats_friendly=True,
        recommended_for=["Director of Engineering", "VP of Technology", "Principal Architect", "Head of AI", "Engineering Manager"],
        default_theme=ThemeConfig(
            theme_id="executive_navy",
            name="Executive Navy",
            primary_color="#0F2942",
            secondary_color="#2C4D6F",
            accent_color="#8C6D3B",
            text_color="#1F2937",
            muted_text="#4B5563",
            background_color="#FFFFFF",
            card_background="#F8FAFC",
            font_heading="'Cinzel', 'Georgia', serif",
            font_body="'Inter', sans-serif",
            font_size_base="10pt",
            line_height="1.5",
        ),
        default_sections=_standard_sections(),
        css_template="""
            .resume-header { border-bottom: 2px solid var(--primary); padding-bottom: 16px; margin-bottom: 20px; text-align: center; }
            .candidate-name { font-size: 26pt; font-weight: 700; color: var(--primary); letter-spacing: 0.5px; }
            .candidate-title { font-size: 13pt; color: var(--secondary); font-weight: 500; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }
            .contact-line { font-size: 9pt; color: var(--muted); margin-top: 8px; display: flex; justify-content: center; gap: 16px; flex-wrap: wrap; }
            .section-title { font-size: 12pt; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #CBD5E1; padding-bottom: 4px; margin: 18px 0 10px; }
            .job-entry, .project-entry { margin-bottom: 14px; }
            .job-header { display: flex; justify-content: space-between; font-weight: 600; font-size: 10.5pt; color: var(--text); }
            .job-sub { display: flex; justify-content: space-between; font-size: 9.5pt; color: var(--secondary); margin-bottom: 4px; font-style: italic; }
            .bullet-list { margin: 4px 0 0 16px; padding: 0; }
            .bullet-list li { margin-bottom: 3px; font-size: 9.5pt; line-height: 1.45; }
        """
    ),

    # 2. Modern Minimal
    TemplateType.MODERN_MINIMAL: TemplateDefinition(
        template_id=TemplateType.MODERN_MINIMAL,
        name="Modern Minimal",
        description="Clean monochromatic typography, ample breathing room, subtle horizontal rules, and high visual clarity.",
        category="Modern",
        ats_friendly=True,
        recommended_for=["Senior Software Engineer", "Product Designer", "Full Stack Developer", "Engineering Consultant"],
        default_theme=ThemeConfig(
            theme_id="modern_minimal_dark",
            name="Minimal Slate",
            primary_color="#18181B",
            secondary_color="#52525B",
            accent_color="#2563EB",
            text_color="#27272A",
            muted_text="#71717A",
            background_color="#FFFFFF",
            card_background="#FAFAFA",
            font_heading="'Outfit', 'Inter', sans-serif",
            font_body="'Inter', sans-serif",
            font_size_base="10pt",
            line_height="1.45",
        ),
        default_sections=_standard_sections(),
        css_template="""
            .resume-header { margin-bottom: 20px; }
            .candidate-name { font-size: 24pt; font-weight: 700; color: var(--primary); }
            .candidate-title { font-size: 12pt; color: var(--accent); font-weight: 600; margin-top: 2px; }
            .contact-line { font-size: 9pt; color: var(--muted); margin-top: 6px; display: flex; gap: 14px; flex-wrap: wrap; }
            .section-title { font-size: 11pt; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 1.2px; margin: 16px 0 8px; border-bottom: 1.5px solid var(--primary); padding-bottom: 3px; }
            .job-header { display: flex; justify-content: space-between; font-weight: 600; font-size: 10pt; }
            .job-sub { display: flex; justify-content: space-between; font-size: 9pt; color: var(--secondary); margin-bottom: 4px; }
            .bullet-list { margin: 4px 0 0 14px; padding: 0; }
            .bullet-list li { margin-bottom: 2.5px; font-size: 9.5pt; }
        """
    ),

    # 3. ATS Classic
    TemplateType.ATS_CLASSIC: TemplateDefinition(
        template_id=TemplateType.ATS_CLASSIC,
        name="ATS Classic Standard",
        description="Single-column, zero-table, standard bulleted layout engineered specifically for 100% flawless automated parsing across Taleo, Workday, Greenhouse, and Lever ATS systems.",
        category="ATS Standard",
        ats_friendly=True,
        recommended_for=["All Roles", "Corporate Applications", "High-Volume Portal Submissions", "Enterprise Tech"],
        default_theme=ThemeConfig(
            theme_id="ats_pure",
            name="ATS Pure",
            primary_color="#000000",
            secondary_color="#333333",
            accent_color="#000000",
            text_color="#111111",
            muted_text="#444444",
            background_color="#FFFFFF",
            font_heading="'Arial', 'Helvetica', sans-serif",
            font_body="'Arial', 'Helvetica', sans-serif",
            font_size_base="10pt",
            line_height="1.4",
            margin_pt=36,
        ),
        default_sections=_standard_sections(),
        css_template="""
            .resume-header { text-align: center; margin-bottom: 16px; }
            .candidate-name { font-size: 20pt; font-weight: bold; text-transform: uppercase; color: #000; }
            .contact-line { font-size: 9.5pt; color: #333; margin-top: 4px; }
            .section-title { font-size: 11pt; font-weight: bold; text-transform: uppercase; border-bottom: 1px solid #000; padding-bottom: 2px; margin: 14px 0 8px; }
            .job-entry, .project-entry { margin-bottom: 10px; }
            .job-header { display: flex; justify-content: space-between; font-weight: bold; font-size: 10pt; }
            .job-sub { display: flex; justify-content: space-between; font-size: 9.5pt; color: #333; }
            .bullet-list { margin: 3px 0 0 16px; padding: 0; }
            .bullet-list li { margin-bottom: 2px; font-size: 9.5pt; line-height: 1.35; }
            .skills-text-line { font-size: 9.5pt; line-height: 1.4; margin-bottom: 3px; }
        """
    ),

    # 4. Technical Engineer
    TemplateType.TECHNICAL_ENGINEER: TemplateDefinition(
        template_id=TemplateType.TECHNICAL_ENGINEER,
        name="Technical Engineer",
        description="Structured tech matrix, quantifiable metrics callout, bold engineering emphasis, and dedicated tooling section.",
        category="Engineering",
        ats_friendly=True,
        recommended_for=["Senior Systems Engineer", "Backend Engineer", "Infrastructure Engineer", "DevOps / SRE Architect"],
        default_theme=ThemeConfig(
            theme_id="tech_slate_teal",
            name="Tech Slate & Teal",
            primary_color="#1E293B",
            secondary_color="#334155",
            accent_color="#0EA5E9",
            text_color="#0F172A",
            muted_text="#64748B",
            background_color="#FFFFFF",
            card_background="#F1F5F9",
            font_heading="'Inter', sans-serif",
            font_body="'Inter', sans-serif",
            font_size_base="10pt",
            line_height="1.45",
        ),
        default_sections=_standard_sections(),
        css_template="""
            .resume-header { border-left: 4px solid var(--accent); padding-left: 12px; margin-bottom: 18px; }
            .candidate-name { font-size: 22pt; font-weight: 800; color: var(--primary); }
            .candidate-title { font-size: 12pt; color: var(--accent); font-weight: 600; margin-top: 2px; }
            .contact-line { font-size: 9pt; color: var(--muted); margin-top: 6px; display: flex; gap: 14px; flex-wrap: wrap; }
            .section-title { font-size: 11pt; font-weight: 700; color: var(--primary); border-bottom: 1.5px solid var(--accent); padding-bottom: 3px; margin: 16px 0 8px; text-transform: uppercase; letter-spacing: 0.8px; }
            .skills-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; margin-bottom: 8px; font-size: 9.5pt; }
            .job-header { display: flex; justify-content: space-between; font-weight: 700; font-size: 10pt; }
            .job-sub { display: flex; justify-content: space-between; font-size: 9pt; color: var(--secondary); margin-bottom: 4px; }
            .bullet-list { margin: 4px 0 0 14px; padding: 0; }
            .bullet-list li { margin-bottom: 2.5px; font-size: 9.5pt; }
        """
    ),

    # 5. Developer
    TemplateType.DEVELOPER: TemplateDefinition(
        template_id=TemplateType.DEVELOPER,
        name="Developer & Hacker",
        description="Code-aesthetic monospaced touches, GitHub link highlights, tech stack badges, and terminal-inspired section dividers.",
        category="Software Development",
        ats_friendly=True,
        recommended_for=["Full Stack Developer", "Frontend Engineer", "Open Source Contributor", "Python/Rust Developer"],
        default_theme=ThemeConfig(
            theme_id="dev_dark_emerald",
            name="Developer Emerald",
            primary_color="#0F172A",
            secondary_color="#334155",
            accent_color="#10B981",
            text_color="#1E293B",
            muted_text="#64748B",
            background_color="#FFFFFF",
            card_background="#F8FAFC",
            font_heading="'Inter', sans-serif",
            font_body="'Inter', sans-serif",
            font_code="'Share Tech Mono', monospace",
            font_size_base="9.5pt",
            line_height="1.45",
        ),
        default_sections=_standard_sections(),
        css_template="""
            .resume-header { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 14px 16px; margin-bottom: 18px; }
            .candidate-name { font-size: 22pt; font-weight: 800; color: var(--primary); }
            .candidate-title { font-size: 11pt; color: var(--accent); font-weight: 600; font-family: var(--font-code); }
            .contact-line { font-size: 8.5pt; color: var(--muted); margin-top: 6px; display: flex; gap: 12px; flex-wrap: wrap; }
            .section-title { font-size: 10.5pt; font-weight: 700; color: var(--primary); text-transform: uppercase; margin: 14px 0 8px; border-bottom: 1px dashed #CBD5E1; padding-bottom: 2px; }
            .tech-pill { display: inline-block; background: #E2E8F0; color: #1E293B; font-size: 8pt; font-family: var(--font-code); padding: 1px 6px; border-radius: 3px; margin: 1px 3px 1px 0; }
            .job-header { display: flex; justify-content: space-between; font-weight: 600; font-size: 9.5pt; }
            .job-sub { display: flex; justify-content: space-between; font-size: 8.5pt; color: var(--secondary); }
            .bullet-list { margin: 3px 0 0 14px; padding: 0; }
            .bullet-list li { margin-bottom: 2px; font-size: 9pt; }
        """
    ),

    # 6. Fresh Graduate
    TemplateType.FRESH_GRADUATE: TemplateDefinition(
        template_id=TemplateType.FRESH_GRADUATE,
        name="Fresh Graduate & Campus",
        description="Prioritizes academic credentials, coursework, capstone projects, internships, and technical certifications.",
        category="Entry Level",
        ats_friendly=True,
        recommended_for=["Junior Engineer", "Graduate Software Trainee", "Intern", "Associate Data Scientist"],
        default_theme=ThemeConfig(
            theme_id="campus_indigo",
            name="Campus Indigo",
            primary_color="#312E81",
            secondary_color="#4338CA",
            accent_color="#6366F1",
            text_color="#1E1B4B",
            muted_text="#6B7280",
            background_color="#FFFFFF",
            font_heading="'Outfit', 'Inter', sans-serif",
            font_body="'Inter', sans-serif",
            font_size_base="10pt",
            line_height="1.45",
        ),
        default_sections=[
            SectionConfig(section_id="summary", title="Objective & Summary", visible=True, order=1, layout="standard"),
            SectionConfig(section_id="education", title="Education & Academic Qualifications", visible=True, order=2, layout="standard"),
            SectionConfig(section_id="skills", title="Technical Skills & Proficiencies", visible=True, order=3, layout="pills"),
            SectionConfig(section_id="projects", title="Academic & Personal Engineering Projects", visible=True, order=4, layout="standard"),
            SectionConfig(section_id="experience", title="Internships & Practical Experience", visible=True, order=5, layout="standard"),
            SectionConfig(section_id="certifications", title="Certifications & Training", visible=True, order=6, layout="standard"),
            SectionConfig(section_id="achievements", title="Extracurricular & Academic Honors", visible=True, order=7, layout="standard"),
        ],
        css_template="""
            .resume-header { text-align: center; border-bottom: 2px solid var(--accent); padding-bottom: 12px; margin-bottom: 16px; }
            .candidate-name { font-size: 22pt; font-weight: 700; color: var(--primary); }
            .candidate-title { font-size: 11pt; color: var(--secondary); font-weight: 500; }
            .contact-line { font-size: 9pt; color: var(--muted); margin-top: 4px; display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; }
            .section-title { font-size: 11pt; font-weight: 700; color: var(--primary); text-transform: uppercase; border-bottom: 1px solid #E0E7FF; padding-bottom: 2px; margin: 14px 0 8px; }
            .job-header, .edu-header { display: flex; justify-content: space-between; font-weight: 600; font-size: 10pt; }
            .job-sub, .edu-sub { display: flex; justify-content: space-between; font-size: 9pt; color: var(--secondary); }
            .bullet-list { margin: 3px 0 0 14px; padding: 0; }
            .bullet-list li { margin-bottom: 2px; font-size: 9.5pt; }
        """
    ),

    # 7. Startup / Product
    TemplateType.STARTUP_PRODUCT: TemplateDefinition(
        template_id=TemplateType.STARTUP_PRODUCT,
        name="Startup & Product Innovator",
        description="High-impact metric callouts, product release ownership, bold vibrant accents, and cross-functional agile framing.",
        category="Product & Growth",
        ats_friendly=True,
        recommended_for=["Product Engineer", "Founding Engineer", "Technical Product Manager", "Growth Engineer"],
        default_theme=ThemeConfig(
            theme_id="startup_violet",
            name="Startup Violet",
            primary_color="#2E1065",
            secondary_color="#581C87",
            accent_color="#8B5CF6",
            text_color="#1E1B4B",
            muted_text="#6B7280",
            background_color="#FFFFFF",
            font_heading="'Outfit', 'Inter', sans-serif",
            font_body="'Inter', sans-serif",
            font_size_base="10pt",
            line_height="1.45",
        ),
        default_sections=_standard_sections(),
        css_template="""
            .resume-header { margin-bottom: 18px; }
            .candidate-name { font-size: 24pt; font-weight: 800; color: var(--primary); }
            .candidate-title { font-size: 12pt; color: var(--accent); font-weight: 600; }
            .contact-line { font-size: 9pt; color: var(--muted); margin-top: 4px; display: flex; gap: 14px; flex-wrap: wrap; }
            .section-title { font-size: 11pt; font-weight: 700; color: var(--primary); border-bottom: 2px solid var(--accent); padding-bottom: 2px; margin: 14px 0 8px; text-transform: uppercase; }
            .job-header { display: flex; justify-content: space-between; font-weight: 700; font-size: 10pt; }
            .job-sub { display: flex; justify-content: space-between; font-size: 9pt; color: var(--secondary); font-weight: 500; }
            .bullet-list { margin: 4px 0 0 14px; padding: 0; }
            .bullet-list li { margin-bottom: 3px; font-size: 9.5pt; }
        """
    ),

    # 8. AI / Data
    TemplateType.AI_DATA: TemplateDefinition(
        template_id=TemplateType.AI_DATA,
        name="AI & Machine Learning Architect",
        description="Designed specifically for AI/ML researchers and engineers with dedicated sections for model architectures, pipelines, datasets, and benchmark results.",
        category="Artificial Intelligence",
        ats_friendly=True,
        recommended_for=["Autonomous AI Architect", "AI Research Engineer", "LLM Systems Engineer", "Data Scientist", "MLOps Engineer"],
        default_theme=ThemeConfig(
            theme_id="ai_cyan_dark",
            name="AI Cyan Matrix",
            primary_color="#0A2540",
            secondary_color="#204060",
            accent_color="#00A3C4",
            text_color="#0F172A",
            muted_text="#475569",
            background_color="#FFFFFF",
            font_heading="'Inter', sans-serif",
            font_body="'Inter', sans-serif",
            font_size_base="9.5pt",
            line_height="1.45",
        ),
        default_sections=[
            SectionConfig(section_id="summary", title="AI Systems & Research Summary", visible=True, order=1, layout="standard"),
            SectionConfig(section_id="skills", title="AI/ML Models, Frameworks & Tooling", visible=True, order=2, layout="grid"),
            SectionConfig(section_id="experience", title="AI Engineering & Industry Experience", visible=True, order=3, layout="standard"),
            SectionConfig(section_id="projects", title="Featured Autonomous Systems & ML Projects", visible=True, order=4, layout="standard"),
            SectionConfig(section_id="certifications", title="AI Certifications & Specialized Credentials", visible=True, order=5, layout="standard"),
            SectionConfig(section_id="education", title="Academic Background in Computing & AI", visible=True, order=6, layout="standard"),
            SectionConfig(section_id="achievements", title="Research, Hackathons & Benchmark Honors", visible=True, order=7, layout="standard"),
        ],
        css_template="""
            .resume-header { border-bottom: 2px solid var(--accent); padding-bottom: 12px; margin-bottom: 16px; }
            .candidate-name { font-size: 22pt; font-weight: 800; color: var(--primary); letter-spacing: -0.5px; }
            .candidate-title { font-size: 11.5pt; color: var(--accent); font-weight: 600; margin-top: 2px; }
            .contact-line { font-size: 8.5pt; color: var(--muted); margin-top: 6px; display: flex; gap: 12px; flex-wrap: wrap; }
            .section-title { font-size: 10.5pt; font-weight: 700; color: var(--primary); text-transform: uppercase; border-bottom: 1px solid #CBD5E1; padding-bottom: 2px; margin: 14px 0 8px; letter-spacing: 0.5px; }
            .job-header { display: flex; justify-content: space-between; font-weight: 700; font-size: 9.5pt; color: var(--primary); }
            .job-sub { display: flex; justify-content: space-between; font-size: 8.5pt; color: var(--secondary); font-style: italic; }
            .bullet-list { margin: 3px 0 0 14px; padding: 0; }
            .bullet-list li { margin-bottom: 2.5px; font-size: 9pt; }
        """
    ),

    # 9. Cybersecurity
    TemplateType.CYBERSECURITY: TemplateDefinition(
        template_id=TemplateType.CYBERSECURITY,
        name="Cybersecurity & Defense Specialist",
        description="Focused on vulnerability mitigation, certifications (CISSP, CEH, OSCP), threat modeling, incident response, and zero-trust systems.",
        category="Security",
        ats_friendly=True,
        recommended_for=["Cybersecurity Analyst", "Security Architect", "Red Team / Penetration Tester", "Cloud Security Engineer"],
        default_theme=ThemeConfig(
            theme_id="sec_crimson_slate",
            name="Security Slate",
            primary_color="#18181B",
            secondary_color="#3F3F46",
            accent_color="#DC2626",
            text_color="#18181B",
            muted_text="#52525B",
            background_color="#FFFFFF",
            font_heading="'Share Tech Mono', 'Inter', monospace",
            font_body="'Inter', sans-serif",
            font_code="'Share Tech Mono', monospace",
            font_size_base="9.5pt",
            line_height="1.4",
        ),
        default_sections=[
            SectionConfig(section_id="summary", title="Security Profile & Threat Posture", visible=True, order=1, layout="standard"),
            SectionConfig(section_id="certifications", title="Security Credentials & Certifications", visible=True, order=2, layout="standard"),
            SectionConfig(section_id="skills", title="Security Tooling & Defense Capabilities", visible=True, order=3, layout="pills"),
            SectionConfig(section_id="experience", title="Security Engineering & Defense Experience", visible=True, order=4, layout="standard"),
            SectionConfig(section_id="projects", title="Security Audits & Infrastructure Hardening", visible=True, order=5, layout="standard"),
            SectionConfig(section_id="education", title="Education & Specialized Training", visible=True, order=6, layout="standard"),
            SectionConfig(section_id="achievements", title="CVE Disclosures & Security Honors", visible=True, order=7, layout="standard"),
        ],
        css_template="""
            .resume-header { border-left: 3px solid var(--accent); padding-left: 10px; margin-bottom: 14px; }
            .candidate-name { font-size: 20pt; font-weight: 800; color: var(--primary); font-family: var(--font-code); }
            .candidate-title { font-size: 10.5pt; color: var(--accent); font-weight: 600; font-family: var(--font-code); }
            .contact-line { font-size: 8.5pt; color: var(--muted); margin-top: 4px; display: flex; gap: 10px; flex-wrap: wrap; font-family: var(--font-code); }
            .section-title { font-size: 10pt; font-weight: 700; color: var(--primary); text-transform: uppercase; border-bottom: 1px solid #D4D4D8; padding-bottom: 2px; margin: 12px 0 6px; font-family: var(--font-code); }
            .job-header { display: flex; justify-content: space-between; font-weight: 700; font-size: 9.5pt; }
            .job-sub { display: flex; justify-content: space-between; font-size: 8.5pt; color: var(--secondary); }
            .bullet-list { margin: 3px 0 0 14px; padding: 0; }
            .bullet-list li { margin-bottom: 2px; font-size: 9pt; }
        """
    ),

    # 10. Compact One-Page
    TemplateType.COMPACT_ONE_PAGE: TemplateDefinition(
        template_id=TemplateType.COMPACT_ONE_PAGE,
        name="Compact One-Page",
        description="High-density, space-optimized layout engineered to present comprehensive experience within exactly 1 printed page.",
        category="Compact",
        ats_friendly=True,
        recommended_for=["All Roles", "Rapid Screenings", "Career Fairs", "Executive Briefings"],
        default_theme=ThemeConfig(
            theme_id="compact_navy",
            name="Compact Navy",
            primary_color="#1E3A8A",
            secondary_color="#3B82F6",
            accent_color="#2563EB",
            text_color="#111827",
            muted_text="#4B5563",
            background_color="#FFFFFF",
            font_heading="'Inter', sans-serif",
            font_body="'Inter', sans-serif",
            font_size_base="9pt",
            line_height="1.35",
            margin_pt=24,  # Tight 0.33in margin
        ),
        default_sections=_standard_sections(),
        css_template="""
            .resume-header { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1.5px solid var(--primary); padding-bottom: 6px; margin-bottom: 10px; }
            .candidate-name { font-size: 18pt; font-weight: 800; color: var(--primary); line-height: 1.1; }
            .candidate-title { font-size: 10pt; color: var(--secondary); font-weight: 600; }
            .contact-line { font-size: 8pt; color: var(--muted); text-align: right; line-height: 1.3; }
            .section-title { font-size: 9.5pt; font-weight: 700; color: var(--primary); text-transform: uppercase; border-bottom: 1px solid #CBD5E1; padding-bottom: 1px; margin: 8px 0 4px; }
            .job-entry, .project-entry { margin-bottom: 6px; }
            .job-header { display: flex; justify-content: space-between; font-weight: 700; font-size: 9pt; }
            .job-sub { display: flex; justify-content: space-between; font-size: 8pt; color: var(--secondary); }
            .bullet-list { margin: 2px 0 0 12px; padding: 0; }
            .bullet-list li { margin-bottom: 1.5px; font-size: 8.5pt; line-height: 1.3; }
        """
    ),
}


def get_template(template_id: Union[TemplateType, str]) -> TemplateDefinition:
    """Retrieve template definition by ID with fallback to ATS_CLASSIC."""
    key = template_id if isinstance(template_id, TemplateType) else TemplateType.ATS_CLASSIC
    if isinstance(template_id, str):
        try:
            key = TemplateType(template_id.lower())
        except Exception:
            key = TemplateType.ATS_CLASSIC
    return TEMPLATES.get(key, TEMPLATES[TemplateType.ATS_CLASSIC])


def list_templates() -> List[Dict[str, Any]]:
    """Return catalog of all available native templates."""
    return [t.to_dict() for t in TEMPLATES.values()]
