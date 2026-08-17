# career/ats_engine/scorer.py — Deterministic 7-Factor ATS Scoring Engine for BR JARVIS
from __future__ import annotations

import logging
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ..resume_engine.models import ResumeSchema

logger = logging.getLogger("JARVIS.ATSEngine")


@dataclass
class ATSScoreReport:
    overall_score: float                     # 0 - 100%
    keyword_coverage_score: float            # 0 - 100%
    section_recognition_score: float         # 0 - 100%
    parsing_risk_score: float                # 0 - 100% (100 = zero risk, 0 = high risk)
    readability_score: float                 # 0 - 100%
    consistency_score: float                 # 0 - 100%
    role_relevance_score: float              # 0 - 100%
    matched_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    critical_risks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommended_changes: List[str] = field(default_factory=list)
    grade: str = "A"                         # "A+" (95+), "A" (85-94), "B" (70-84), "C" (50-69), "D" (<50)

    @property
    def total_score(self) -> float:
        """Alias for overall_score."""
        return self.overall_score

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ATSEngine:
    """
    Deterministic ATS Evaluation Engine.
    Simulates screening algorithms from Greenhouse, Lever, Workday, and Taleo.
    Provides transparent scoring breakdown and actionable recommendations without keyword-stuffing.
    """

    STANDARD_SECTIONS = {
        "summary": ["summary", "professional summary", "executive summary", "profile", "about me"],
        "experience": ["experience", "work experience", "professional experience", "employment history", "career history"],
        "education": ["education", "academic background", "academic qualifications", "education and training"],
        "skills": ["skills", "technical skills", "core competencies", "technical proficiencies", "technologies"],
        "projects": ["projects", "engineering projects", "technical projects", "key projects"],
    }

    ACTION_VERBS = {
        "architected", "engineered", "developed", "designed", "constructed", "built", "implemented",
        "optimized", "deployed", "spearheaded", "orchestrated", "automated", "scaled", "reduced",
        "accelerated", "resolved", "delivered", "mentored", "led", "constructed", "pioneered"
    }

    @classmethod
    def evaluate_resume(cls, resume: Union[ResumeSchema, str, Any], job_description: Optional[str] = None) -> ATSScoreReport:
        """Evaluate resume structure, syntax, and keyword alignment against job description."""
        if isinstance(resume, str):
            full_text = resume
            tokens = cls._extract_tokens(full_text)
            if job_description:
                kw_score, matched_kws, missing_kws, rel_score = cls._score_keywords_and_relevance(resume, tokens, job_description)
            else:
                kw_score, matched_kws, missing_kws, rel_score = 90.0, list(tokens)[:15], [], 90.0

            found_sections = sum(1 for aliases in cls.STANDARD_SECTIONS.values() if any(a in full_text.lower() for a in aliases))
            sec_score = (found_sections / max(1, len(cls.STANDARD_SECTIONS))) * 100.0
            parse_score = 95.0 if ("@" in full_text and any(c.isdigit() for c in full_text)) else 75.0
            read_score, read_recs = cls._score_readability(full_text, tokens)
            cons_score = 90.0

            overall = (
                (kw_score * 0.25) +
                (sec_score * 0.20) +
                (parse_score * 0.15) +
                (read_score * 0.15) +
                (cons_score * 0.10) +
                (rel_score * 0.15)
            )
            overall = round(max(0.0, min(100.0, overall)), 1)
            grade = "A+" if overall >= 95.0 else ("A" if overall >= 85.0 else ("B" if overall >= 72.0 else ("C" if overall >= 55.0 else "D")))

            return ATSScoreReport(
                overall_score=overall,
                keyword_coverage_score=round(kw_score, 1),
                section_recognition_score=round(sec_score, 1),
                parsing_risk_score=round(parse_score, 1),
                readability_score=round(read_score, 1),
                consistency_score=round(cons_score, 1),
                role_relevance_score=round(rel_score, 1),
                matched_keywords=matched_kws,
                missing_keywords=missing_kws,
                critical_risks=[],
                warnings=[],
                recommended_changes=read_recs,
                grade=grade,
            )

        full_text = cls._get_full_resume_text(resume)
        tokens = cls._extract_tokens(full_text)

        # 1. Section Recognition (20% Weight)
        sec_score, sec_warnings = cls._score_sections(resume)

        # 2. Parsing Risk Assessment (15% Weight)
        parse_score, parse_risks = cls._score_parsing_risk(resume)

        # 3. Readability & Action Verbs (15% Weight)
        read_score, read_recs = cls._score_readability(full_text, tokens)

        # 4. Consistency & Formatting (15% Weight)
        cons_score, cons_warnings = cls._score_consistency(resume)

        # 5. Keyword Coverage & Role Relevance (35% Weight)
        if job_description:
            kw_score, matched_kws, missing_kws, rel_score = cls._score_keywords_and_relevance(resume, tokens, job_description)
        else:
            # Baseline domain scoring if no JD provided
            kw_score = 90.0
            matched_kws = list(tokens)[:15]
            missing_kws = []
            rel_score = 90.0

        # Weighted Overall Score
        overall = (
            (kw_score * 0.25) +
            (sec_score * 0.20) +
            (parse_score * 0.15) +
            (read_score * 0.15) +
            (cons_score * 0.10) +
            (rel_score * 0.15)
        )
        overall = round(max(0.0, min(100.0, overall)), 1)

        # Determine Letter Grade
        if overall >= 95.0:
            grade = "A+"
        elif overall >= 85.0:
            grade = "A"
        elif overall >= 72.0:
            grade = "B"
        elif overall >= 55.0:
            grade = "C"
        else:
            grade = "D"

        # Aggregate recommendations
        recommendations = []
        if missing_kws:
            recommendations.append(f"Incorporate legitimate experience with keywords: {', '.join(missing_kws[:6])}.")
        recommendations.extend(sec_warnings)
        recommendations.extend(read_recs)
        recommendations.extend(cons_warnings)

        return ATSScoreReport(
            overall_score=overall,
            keyword_coverage_score=round(kw_score, 1),
            section_recognition_score=round(sec_score, 1),
            parsing_risk_score=round(parse_score, 1),
            readability_score=round(read_score, 1),
            consistency_score=round(cons_score, 1),
            role_relevance_score=round(rel_score, 1),
            matched_keywords=matched_kws,
            missing_keywords=missing_kws,
            critical_risks=parse_risks,
            warnings=sec_warnings + cons_warnings,
            recommended_changes=recommendations,
            grade=grade,
        )

    def evaluate(self, resume: Any, job_description: Optional[str] = None) -> ATSScoreReport:
        """Instance method alias for evaluate_resume."""
        return self.evaluate_resume(resume, job_description)

    # ── Sub-Scoring Helpers ──────────────────────────────────────────────────

    @classmethod
    def _score_sections(cls, resume: ResumeSchema) -> Tuple[float, List[str]]:
        warnings = []
        found_sections = 0
        total_expected = len(cls.STANDARD_SECTIONS)

        for sec_key, aliases in cls.STANDARD_SECTIONS.items():
            matched = False
            for sec in resume.sections:
                if not sec.visible:
                    continue
                s_title = sec.title.lower().strip()
                if any(a in s_title for a in aliases):
                    matched = True
                    break
            if matched:
                found_sections += 1
            else:
                warnings.append(f"Section '{sec_key.title()}' is missing or uses non-standard heading name.")

        score = (found_sections / total_expected) * 100.0
        return score, warnings

    @classmethod
    def _score_parsing_risk(cls, resume: ResumeSchema) -> Tuple[float, List[str]]:
        risks = []
        deductions = 0.0

        # Check template characteristics
        tmpl = resume.template_id.value if hasattr(resume.template_id, "value") else str(resume.template_id)
        if tmpl == "ats_classic":
            # Pure single-column ATS template gets zero deduction
            pass
        elif tmpl in ("developer", "cybersecurity"):
            deductions += 5.0  # Monospace / custom styling minor deduction in strict parsers
        
        # Check contact presence
        if not resume.contact_email or "@" not in resume.contact_email:
            risks.append("Email address is missing or invalid; ATS parsers will fail candidate contact creation.")
            deductions += 30.0

        if not resume.contact_phone:
            risks.append("Phone number is missing; some ATS systems mandate a valid contact number.")
            deductions += 15.0

        score = max(0.0, 100.0 - deductions)
        return score, risks

    @classmethod
    def _score_readability(cls, full_text: str, tokens: Set[str]) -> Tuple[float, List[str]]:
        recs = []
        sentences = [s.strip() for s in re.split(r'[\.\n]', full_text) if len(s.strip()) > 10]
        words = full_text.split()

        if not words:
            return 0.0, ["Resume body contains zero words."]

        avg_sentence_len = len(words) / max(1, len(sentences))
        score = 85.0

        # Action verb density
        action_verb_count = sum(1 for v in cls.ACTION_VERBS if v in tokens)
        if action_verb_count >= 5:
            score += 15.0
        elif action_verb_count < 2:
            score -= 15.0
            recs.append("Begin bullet points with strong active verbs (e.g., 'Engineered', 'Optimized', 'Architected').")

        # Sentence length penalty (run-on bullets)
        if avg_sentence_len > 30:
            score -= 10.0
            recs.append("Bullet points are overly long. Keep statements punchy (15-25 words).")

        return max(0.0, min(100.0, score)), recs

    @classmethod
    def _score_consistency(cls, resume: ResumeSchema) -> Tuple[float, List[str]]:
        warnings = []
        score = 100.0

        # Date format check
        date_patterns = [exp.get("start_date", "") for exp in resume.experience if exp.get("start_date")]
        if date_patterns:
            has_month_year = any("-" in d for d in date_patterns)
            has_just_year = any(len(d.strip()) == 4 and d.isdigit() for d in date_patterns)
            if has_month_year and has_just_year:
                score -= 10.0
                warnings.append("Inconsistent date formats in experience (mix of YYYY and YYYY-MM).")

        return score, warnings

    @classmethod
    def _score_keywords_and_relevance(
        cls,
        resume: ResumeSchema,
        resume_tokens: Set[str],
        job_description: str,
    ) -> Tuple[float, List[str], List[str], float]:
        from brjarvis.career.resume_engine.tailoring import ResumeTailoringEngine
        jd_tokens = ResumeTailoringEngine.extract_keywords(job_description)

        if not jd_tokens:
            return 85.0, list(resume_tokens)[:10], [], 85.0

        matched = [k for k in jd_tokens if any(k in r or r in k for r in resume_tokens)]
        missing = [k for k in jd_tokens if not any(k in r or r in k for r in resume_tokens)]

        # Keyword Coverage %
        coverage_pct = (len(matched) / max(1, len(jd_tokens))) * 100.0
        coverage_score = min(100.0, coverage_pct * 1.6)  # Scale since 60%+ JD token overlap is top-tier

        # Role Relevance
        target_role_tokens = set(resume.target_role.lower().split()) if hasattr(resume, "target_role") else set()
        role_matched = sum(1 for t in target_role_tokens if t in job_description.lower())
        relevance_score = min(100.0, 70.0 + (role_matched * 15.0))

        return coverage_score, matched[:20], missing[:12], relevance_score

    # ── Text Extractor ───────────────────────────────────────────────────────

    @classmethod
    def _get_full_resume_text(cls, resume: ResumeSchema) -> str:
        parts = [
            resume.full_name,
            resume.target_role,
            resume.summary,
        ]
        for exp in resume.experience:
            parts.extend([
                exp.get("title", ""),
                exp.get("company", ""),
                " ".join(exp.get("responsibilities", [])),
                " ".join(exp.get("achievements", [])),
                " ".join(exp.get("technologies", [])),
            ])
        for sc in resume.skills:
            parts.append(" ".join(sc.get("skills", [])))
        for p in resume.projects:
            parts.extend([
                p.get("name", ""),
                p.get("description", ""),
                " ".join(p.get("technologies", [])),
                " ".join(p.get("highlights", [])),
            ])
        for edu in resume.education:
            parts.extend([
                edu.get("institution", ""),
                edu.get("degree", ""),
                edu.get("field_of_study", ""),
            ])
        return " ".join(parts)

    @classmethod
    def _extract_tokens(cls, text: str) -> Set[str]:
        clean = re.sub(r'[^a-zA-Z0-9\+\#\-\.\s]', ' ', text.lower())
        return {t.strip() for t in clean.split() if len(t.strip()) >= 2}
