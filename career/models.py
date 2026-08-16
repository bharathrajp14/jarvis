# career/models.py — Canonical Structured Models for BR JARVIS Career OS
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union


# ── Provenance & Confidence ──────────────────────────────────────────────────

class FactSource(str, Enum):
    USER_INPUT       = "user_input"
    VERIFIED_DOC     = "verified_doc"
    RESUME_IMPORT    = "resume_import"
    LINKEDIN_IMPORT  = "linkedin_import"
    GITHUB_IMPORT    = "github_import"
    INFERRED         = "inferred"
    UNKNOWN          = "unknown"


@dataclass
class ProfileFact:
    """Represents a discrete verified fact with strict provenance tracking."""
    value: Any
    source: FactSource = FactSource.USER_INPUT
    verified: bool = True
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source.value if isinstance(self.source, FactSource) else str(self.source),
            "verified": self.verified,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProfileFact:
        src = data.get("source", "user_input")
        try:
            source_enum = FactSource(src)
        except Exception:
            source_enum = FactSource.USER_INPUT
        return cls(
            value=data.get("value"),
            source=source_enum,
            verified=data.get("verified", True),
            confidence=data.get("confidence", 1.0),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


# ── Canonical Profile Components ─────────────────────────────────────────────

@dataclass
class ContactInfo:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""  # City, State / Country
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    twitter_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EducationEntry:
    education_id: str = field(default_factory=lambda: f"edu_{uuid.uuid4().hex[:8]}")
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""  # "YYYY-MM" or "YYYY"
    end_date: str = ""    # "YYYY-MM" or "Present"
    grade_or_gpa: str = ""
    location: str = ""
    highlights: List[str] = field(default_factory=list)
    verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExperienceEntry:
    experience_id: str = field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    company: str = ""
    title: str = ""
    location: str = ""
    remote_type: str = "onsite"  # "remote", "hybrid", "onsite"
    start_date: str = ""         # "YYYY-MM"
    end_date: str = ""           # "YYYY-MM" or "Present"
    is_current: bool = False
    responsibilities: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)  # Verified numbers (e.g. "Improved throughput by 42%")
    verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectEntry:
    project_id: str = field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:8]}")
    name: str = ""
    role: str = ""
    description: str = ""
    url: str = ""
    repository_url: str = ""
    technologies: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SkillCategory:
    category: str = "General"  # e.g., "Languages", "Frameworks", "Cloud & DevOps", "Databases", "AI/ML"
    skills: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CertificationEntry:
    cert_id: str = field(default_factory=lambda: f"cert_{uuid.uuid4().hex[:8]}")
    name: str = ""
    issuer: str = ""
    issue_date: str = ""
    expiration_date: str = ""
    credential_id: str = ""
    credential_url: str = ""
    verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AchievementEntry:
    achievement_id: str = field(default_factory=lambda: f"ach_{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    issuer_or_context: str = ""
    date: str = ""
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Target & Preferences ─────────────────────────────────────────────────────

@dataclass
class WorkPreferences:
    target_roles: List[str] = field(default_factory=lambda: ["AI Engineer", "Senior Software Engineer"])
    target_industries: List[str] = field(default_factory=lambda: ["Artificial Intelligence", "Autonomous Systems", "Enterprise Software"])
    target_locations: List[str] = field(default_factory=lambda: ["Remote", "Madurai", "Bengaluru", "Chennai"])
    remote_preference: str = "any"  # "remote_only", "hybrid_preferred", "onsite_ok", "any"
    employment_types: List[str] = field(default_factory=lambda: ["Full-time", "Contract"])
    availability: str = "Immediate / 2 Weeks"
    work_authorization: str = "Authorized to work without sponsorship"
    requires_sponsorship: bool = False
    preferred_companies: List[str] = field(default_factory=list)
    excluded_companies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SalaryPreferences:
    target_annual_salary: float = 0.0
    minimum_annual_salary: float = 0.0
    currency: str = "USD"  # USD, INR, EUR, GBP
    salary_notes: str = "Negotiable based on total equity and benefits package"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Authoritative Master Career Profile ──────────────────────────────────────

@dataclass
class CareerProfile:
    """
    Authoritative Canonical Source of Truth for Career Identity and History.
    Master Profile is immutable against job-specific tailoring.
    """
    profile_id: str = "master_profile"
    version: int = 1
    summary: str = ""
    contact: ContactInfo = field(default_factory=ContactInfo)
    education: List[EducationEntry] = field(default_factory=list)
    experience: List[ExperienceEntry] = field(default_factory=list)
    projects: List[ProjectEntry] = field(default_factory=list)
    skills: List[SkillCategory] = field(default_factory=list)
    certifications: List[CertificationEntry] = field(default_factory=list)
    achievements: List[AchievementEntry] = field(default_factory=list)
    preferences: WorkPreferences = field(default_factory=WorkPreferences)
    salary: SalaryPreferences = field(default_factory=SalaryPreferences)
    custom_sections: Dict[str, List[str]] = field(default_factory=dict)
    provenance: Dict[str, ProfileFact] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "version": self.version,
            "summary": self.summary,
            "contact": self.contact.to_dict(),
            "education": [e.to_dict() for e in self.education],
            "experience": [e.to_dict() for e in self.experience],
            "projects": [p.to_dict() for p in self.projects],
            "skills": [s.to_dict() for s in self.skills],
            "certifications": [c.to_dict() for c in self.certifications],
            "achievements": [a.to_dict() for a in self.achievements],
            "preferences": self.preferences.to_dict(),
            "salary": self.salary.to_dict(),
            "custom_sections": self.custom_sections,
            "provenance": {k: v.to_dict() for k, v in self.provenance.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CareerProfile:
        contact_data = data.get("contact", {})
        contact = ContactInfo(**{k: v for k, v in contact_data.items() if k in ContactInfo.__dataclass_fields__})

        edu_list = [
            EducationEntry(**{k: v for k, v in e.items() if k in EducationEntry.__dataclass_fields__})
            for e in data.get("education", [])
        ]
        exp_list = [
            ExperienceEntry(**{k: v for k, v in e.items() if k in ExperienceEntry.__dataclass_fields__})
            for e in data.get("experience", [])
        ]
        proj_list = [
            ProjectEntry(**{k: v for k, v in p.items() if k in ProjectEntry.__dataclass_fields__})
            for p in data.get("projects", [])
        ]
        skills_list = [
            SkillCategory(**{k: v for k, v in s.items() if k in SkillCategory.__dataclass_fields__})
            for s in data.get("skills", [])
        ]
        cert_list = [
            CertificationEntry(**{k: v for k, v in c.items() if k in CertificationEntry.__dataclass_fields__})
            for c in data.get("certifications", [])
        ]
        ach_list = [
            AchievementEntry(**{k: v for k, v in a.items() if k in AchievementEntry.__dataclass_fields__})
            for a in data.get("achievements", [])
        ]
        pref_data = data.get("preferences", {})
        pref = WorkPreferences(**{k: v for k, v in pref_data.items() if k in WorkPreferences.__dataclass_fields__})

        salary_data = data.get("salary", {})
        salary = SalaryPreferences(**{k: v for k, v in salary_data.items() if k in SalaryPreferences.__dataclass_fields__})

        provenance_data = {
            k: ProfileFact.from_dict(v) for k, v in data.get("provenance", {}).items()
        }

        return cls(
            profile_id=data.get("profile_id", "master_profile"),
            version=data.get("version", 1),
            summary=data.get("summary", ""),
            contact=contact,
            education=edu_list,
            experience=exp_list,
            projects=proj_list,
            skills=skills_list,
            certifications=cert_list,
            achievements=ach_list,
            preferences=pref,
            salary=salary,
            custom_sections=data.get("custom_sections", {}),
            provenance=provenance_data,
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


# ── Job Engine Models ────────────────────────────────────────────────────────

@dataclass
class JobPosting:
    job_id: str
    source: str                 # "greenhouse", "lever", "ashby", "company_portal", "linkedin", "browser_discovery"
    platform: str
    company: str
    title: str
    location: str
    remote_type: str = "unknown"  # "remote", "hybrid", "onsite", "unknown"
    employment_type: str = "Full-time"
    salary: str = ""
    description: str = ""
    requirements: List[str] = field(default_factory=list)
    preferred_requirements: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    experience_level: str = ""  # "Entry", "Mid", "Senior", "Lead", "Principal"
    education: str = ""
    application_url: str = ""
    application_method: str = "web_form"  # "official_api", "web_form", "email", "manual"
    posted_date: str = ""
    closing_date: str = ""
    source_url: str = ""
    discovered_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchBreakdown:
    overall_score: float = 0.0          # 0 - 100%
    skills_score: float = 0.0           # 0 - 100%
    experience_score: float = 0.0       # 0 - 100%
    education_score: float = 0.0        # 0 - 100%
    location_score: float = 0.0         # 0 - 100%
    role_fit_score: float = 0.0         # 0 - 100%
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    key_strengths: List[str] = field(default_factory=list)
    weak_areas: List[str] = field(default_factory=list)
    fit_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Canonical Application CRM & Event Engine Models ──────────────────────────

class ApplicationStatus(str, Enum):
    DISCOVERED               = "DISCOVERED"
    SHORTLISTED              = "SHORTLISTED"
    PREPARING                = "PREPARING"
    READY_FOR_REVIEW         = "READY_FOR_REVIEW"
    APPLICATION_OPENED       = "APPLICATION_OPENED"
    APPLICATION_IN_PROGRESS  = "APPLICATION_IN_PROGRESS"
    SUBMISSION_REQUESTED     = "SUBMISSION_REQUESTED"
    SUBMITTED                = "SUBMITTED"
    SUBMISSION_VERIFIED      = "SUBMISSION_VERIFIED"
    RECRUITER_CONTACTED      = "RECRUITER_CONTACTED"
    SCREENING                = "SCREENING"
    INTERVIEW_REQUESTED      = "INTERVIEW_REQUESTED"
    INTERVIEW_SCHEDULED      = "INTERVIEW_SCHEDULED"
    INTERVIEW_COMPLETED      = "INTERVIEW_COMPLETED"
    TECHNICAL_ROUND          = "TECHNICAL_ROUND"
    FINAL_ROUND              = "FINAL_ROUND"
    OFFER_RECEIVED           = "OFFER_RECEIVED"
    OFFER_ACCEPTED           = "OFFER_ACCEPTED"
    OFFER_DECLINED           = "OFFER_DECLINED"
    REJECTED                 = "REJECTED"
    WITHDRAWN                = "WITHDRAWN"
    FAILED                   = "FAILED"
    MANUAL_ACTION_REQUIRED   = "MANUAL_ACTION_REQUIRED"
    UNKNOWN                  = "UNKNOWN"

    # Backward-compatible aliases
    INTERVIEW = "INTERVIEW_SCHEDULED"
    TECHNICAL = "TECHNICAL_ROUND"
    OFFER = "OFFER_RECEIVED"


class ApplicationEventType(str, Enum):
    APPLICATION_CREATED      = "ApplicationCreated"
    JOB_SHORTLISTED          = "JobShortlisted"
    APPLICATION_PREPARED     = "ApplicationPrepared"
    RESUME_GENERATED         = "ResumeGenerated"
    COVER_LETTER_GENERATED   = "CoverLetterGenerated"
    APPLICATION_OPENED       = "ApplicationOpened"
    APPLICATION_SUBMITTED    = "ApplicationSubmitted"
    SUBMISSION_VERIFIED      = "SubmissionVerified"
    EMAIL_RECEIVED           = "EmailReceived"
    RECRUITER_CONTACTED      = "RecruiterContacted"
    INTERVIEW_REQUESTED      = "InterviewRequested"
    INTERVIEW_SCHEDULED      = "InterviewScheduled"
    INTERVIEW_COMPLETED      = "InterviewCompleted"
    OFFER_DETECTED           = "OfferDetected"
    OFFER_CONFIRMED          = "OfferConfirmed"
    REJECTION_DETECTED       = "RejectionDetected"
    FOLLOWUP_CREATED         = "FollowupCreated"
    FOLLOWUP_COMPLETED       = "FollowupCompleted"


class EmailClassification(str, Enum):
    APPLICATION_CONFIRMATION = "APPLICATION_CONFIRMATION"
    APPLICATION_RECEIVED     = "APPLICATION_RECEIVED"
    RECRUITER_CONTACT        = "RECRUITER_CONTACT"
    SCREENING_REQUEST        = "SCREENING_REQUEST"
    INTERVIEW_REQUEST        = "INTERVIEW_REQUEST"
    INTERVIEW_CONFIRMATION   = "INTERVIEW_CONFIRMATION"
    INTERVIEW_RESCHEDULE     = "INTERVIEW_RESCHEDULE"
    INTERVIEW_REMINDER       = "INTERVIEW_REMINDER"
    TECHNICAL_TEST           = "TECHNICAL_TEST"
    ASSESSMENT               = "ASSESSMENT"
    OFFER                    = "OFFER"
    OFFER_UPDATE             = "OFFER_UPDATE"
    REJECTION                = "REJECTION"
    WITHDRAWAL               = "WITHDRAWAL"
    FOLLOW_UP                = "FOLLOW_UP"
    GENERAL_RECRUITING       = "GENERAL_RECRUITING"
    IRRELEVANT               = "IRRELEVANT"


class OfferStatus(str, Enum):
    OFFER_CANDIDATE = "OFFER_CANDIDATE"
    OFFER_DETECTED  = "OFFER_DETECTED"
    OFFER_CONFIRMED = "OFFER_CONFIRMED"
    OFFER_ACCEPTED  = "OFFER_ACCEPTED"
    OFFER_DECLINED  = "OFFER_DECLINED"
    OFFER_EXPIRED   = "OFFER_EXPIRED"


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class PlatformPolicyState(str, Enum):
    AUTOMATION_ALLOWED = "AUTOMATION_ALLOWED"
    API_ALLOWED        = "API_ALLOWED"
    REVIEW_REQUIRED    = "REVIEW_REQUIRED"
    MANUAL_REQUIRED    = "MANUAL_REQUIRED"
    BLOCKED            = "BLOCKED"
    UNKNOWN            = "UNKNOWN"


@dataclass
class PlatformPolicy:
    platform_name: str
    automation_allowed: bool = False
    api_available: bool = False
    browser_allowed: bool = True
    manual_required: bool = True
    captcha_expected: bool = False
    policy_state: PlatformPolicyState = PlatformPolicyState.REVIEW_REQUIRED
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["policy_state"] = self.policy_state.value
        return d


@dataclass
class ApplicationQuestion:
    question_id: str
    question_text: str
    field_type: str = "text"  # "text", "select", "radio", "checkbox", "file", "number"
    required: bool = True
    suggested_answer: str = ""
    confidence: float = 1.0
    requires_confirmation: bool = False
    user_confirmed: bool = False
    user_override_answer: Optional[str] = None
    sensitive_category: Optional[str] = None  # "work_authorization", "salary", "sponsorship", "eeo", "legal"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicationPackage:
    package_id: str
    job_id: str
    company: str
    role_title: str
    resume_docx_path: str = ""
    resume_pdf_path: str = ""
    resume_html_path: str = ""
    cover_letter_pdf_path: str = ""
    cover_letter_text: str = ""
    answers_json_path: str = ""
    answers_payload: Dict[str, Any] = field(default_factory=dict)
    job_description_html_path: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicationEvent:
    """Immutable audit record for every career state mutation or external signal."""
    event_id: str = field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:10]}")
    application_id: str = ""
    timestamp: float = field(default_factory=time.time)
    source: str = "JARVIS"           # JARVIS, User, Gmail, Outlook, Calendar, Greenhouse, Ashby, Lever, Browser
    actor: str = "system"            # system, user, recruiter, provider
    event_type: ApplicationEventType = ApplicationEventType.APPLICATION_CREATED
    evidence: str = ""
    confidence: float = 1.0
    previous_state: str = ""
    new_state: str = ""
    task_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "application_id": self.application_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "actor": self.actor,
            "event_type": self.event_type.value if isinstance(self.event_type, ApplicationEventType) else str(self.event_type),
            "evidence": self.evidence,
            "confidence": self.confidence,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "task_id": self.task_id,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ApplicationEvent:
        et = d.get("event_type", "ApplicationCreated")
        try:
            et_enum = ApplicationEventType(et)
        except Exception:
            et_enum = ApplicationEventType.APPLICATION_CREATED
        return cls(
            event_id=d.get("event_id", f"ev_{uuid.uuid4().hex[:10]}"),
            application_id=d.get("application_id", ""),
            timestamp=d.get("timestamp", time.time()),
            source=d.get("source", "JARVIS"),
            actor=d.get("actor", "system"),
            event_type=et_enum,
            evidence=d.get("evidence", ""),
            confidence=d.get("confidence", 1.0),
            previous_state=d.get("previous_state", ""),
            new_state=d.get("new_state", ""),
            task_id=d.get("task_id"),
            payload=d.get("payload", {}),
        )


@dataclass(init=False)
class Application:
    """Canonical 32-Field Authoritative Career Application Entity."""
    application_id: str = field(default_factory=lambda: f"APP-{uuid.uuid4().hex[:6].upper()}")
    task_id: Optional[str] = None
    candidate_id: str = "master_candidate"
    job_id: str = ""
    company: str = ""
    job_title: str = ""
    job_url: str = ""
    source: str = "direct"
    platform: str = "Direct"
    location: str = "Remote"
    employment_type: str = "Full-time"
    salary: str = ""
    currency: str = "USD"
    job_description_hash: str = ""
    match_score: float = 0.0
    resume_version: str = "master"
    cover_letter_version: str = ""
    application_package_id: Optional[str] = None
    application_method: str = "web_form"    # official_api, web_form, email, manual
    application_status: ApplicationStatus = ApplicationStatus.DISCOVERED
    submission_status: str = "PENDING"      # PENDING, SUBMITTED, VERIFIED, FAILED
    confirmation_id: Optional[str] = None
    confirmation_url: Optional[str] = None
    date_discovered: str = ""
    date_shortlisted: Optional[str] = None
    date_prepared: Optional[str] = None
    date_applied: Optional[str] = None
    date_verified: Optional[str] = None
    last_updated: float = 0.0
    next_followup: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    notes: List[str] = field(default_factory=list)

    def __init__(
        self,
        application_id: str = "",
        task_id: Optional[str] = None,
        candidate_id: str = "master_candidate",
        job_id: str = "",
        company: str = "",
        job_title: str = "",
        job_url: str = "",
        source: str = "direct",
        platform: str = "Direct",
        location: str = "Remote",
        employment_type: str = "Full-time",
        salary: str = "",
        currency: str = "USD",
        job_description_hash: str = "",
        match_score: float = 0.0,
        resume_version: str = "master",
        cover_letter_version: str = "",
        application_package_id: Optional[str] = None,
        application_method: str = "web_form",
        application_status: ApplicationStatus = ApplicationStatus.DISCOVERED,
        submission_status: str = "PENDING",
        confirmation_id: Optional[str] = None,
        confirmation_url: Optional[str] = None,
        date_discovered: str = "",
        date_shortlisted: Optional[str] = None,
        date_prepared: Optional[str] = None,
        date_applied: Optional[str] = None,
        date_verified: Optional[str] = None,
        last_updated: float = 0.0,
        next_followup: Optional[str] = None,
        priority: PriorityLevel = PriorityLevel.MEDIUM,
        notes: Optional[List[str]] = None,
        **kwargs: Any
    ):
        self.application_id = application_id or f"APP-{uuid.uuid4().hex[:6].upper()}"
        self.task_id = task_id
        self.candidate_id = candidate_id
        self.job_id = job_id
        self.company = company
        self.job_title = job_title or kwargs.get("role_title", "")
        self.job_url = job_url or kwargs.get("application_url", "")
        self.source = source
        self.platform = platform or kwargs.get("source_platform", "Direct")
        self.location = location
        self.employment_type = employment_type
        self.salary = salary
        self.currency = currency
        self.job_description_hash = job_description_hash
        self.match_score = match_score
        self.resume_version = resume_version or kwargs.get("resume_version_id", "master")
        self.cover_letter_version = cover_letter_version
        self.application_package_id = application_package_id or kwargs.get("package_id")
        self.application_method = application_method
        raw_st = kwargs.get("status", application_status)
        if isinstance(raw_st, str):
            try:
                self.application_status = ApplicationStatus(raw_st)
            except Exception:
                self.application_status = ApplicationStatus.DISCOVERED
        else:
            self.application_status = raw_st
        self.submission_status = submission_status
        self.confirmation_id = confirmation_id or kwargs.get("confirmation_id")
        self.confirmation_url = confirmation_url or kwargs.get("confirmation_url")
        self.date_discovered = date_discovered or time.strftime("%Y-%m-%d")
        self.date_shortlisted = date_shortlisted
        self.date_prepared = date_prepared
        self.date_applied = date_applied
        self.date_verified = date_verified
        self.last_updated = last_updated or time.time()
        self.next_followup = next_followup or kwargs.get("follow_up_date")
        self.priority = priority
        self.notes = notes if notes is not None else kwargs.get("notes", [])

    # Legacy property compatibility
    @property
    def status(self) -> ApplicationStatus:
        return self.application_status

    @status.setter
    def status(self, val: ApplicationStatus) -> None:
        self.application_status = val

    @property
    def role_title(self) -> str:
        return self.job_title

    @role_title.setter
    def role_title(self, val: str) -> None:
        self.job_title = val

    @property
    def application_url(self) -> str:
        return self.job_url

    @application_url.setter
    def application_url(self, val: str) -> None:
        self.job_url = val

    @property
    def source_platform(self) -> str:
        return self.platform

    @source_platform.setter
    def source_platform(self, val: str) -> None:
        self.platform = val

    @property
    def applied_at(self) -> Optional[float]:
        return self.last_updated if self.date_applied else None

    @property
    def last_status_change(self) -> float:
        return self.last_updated

    @property
    def package_id(self) -> Optional[str]:
        return self.application_package_id


    @package_id.setter
    def package_id(self, val: Optional[str]) -> None:
        self.application_package_id = val

    @property
    def resume_version_id(self) -> str:
        return self.resume_version

    @resume_version_id.setter
    def resume_version_id(self, val: str) -> None:
        self.resume_version = val

    @property
    def follow_up_date(self) -> Optional[str]:
        return self.next_followup

    @follow_up_date.setter
    def follow_up_date(self, val: Optional[str]) -> None:
        self.next_followup = val

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["application_status"] = self.application_status.value if isinstance(self.application_status, ApplicationStatus) else str(self.application_status)
        d["priority"] = self.priority.value if isinstance(self.priority, PriorityLevel) else str(self.priority)
        # Add legacy fields for backward compatibility
        d["status"] = d["application_status"]
        d["role_title"] = self.job_title
        d["source_platform"] = self.platform
        d["package_id"] = self.application_package_id
        d["resume_version_id"] = self.resume_version
        d["follow_up_date"] = self.next_followup
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Application:
        st_raw = d.get("application_status") or d.get("status", "DISCOVERED")
        try:
            st = ApplicationStatus(st_raw)
        except Exception:
            st = ApplicationStatus.DISCOVERED

        pri_raw = d.get("priority", "MEDIUM")
        try:
            pri = PriorityLevel(pri_raw)
        except Exception:
            pri = PriorityLevel.MEDIUM

        notes_val = d.get("notes", [])
        if isinstance(notes_val, str):
            notes_val = [notes_val]

        return cls(
            application_id=d.get("application_id") or f"APP-{uuid.uuid4().hex[:6].upper()}",
            task_id=d.get("task_id"),
            candidate_id=d.get("candidate_id", "master_candidate"),
            job_id=d.get("job_id", ""),
            company=d.get("company", ""),
            job_title=d.get("job_title") or d.get("role_title", ""),
            job_url=d.get("job_url") or d.get("application_url", ""),
            source=d.get("source", "direct"),
            platform=d.get("platform") or d.get("source_platform", "Direct"),
            location=d.get("location", "Remote"),
            employment_type=d.get("employment_type", "Full-time"),
            salary=d.get("salary", ""),
            currency=d.get("currency", "USD"),
            job_description_hash=d.get("job_description_hash", ""),
            match_score=float(d.get("match_score", 0.0)),
            resume_version=d.get("resume_version") or d.get("resume_version_id", "master"),
            cover_letter_version=d.get("cover_letter_version", ""),
            application_package_id=d.get("application_package_id") or d.get("package_id"),
            application_method=d.get("application_method", "web_form"),
            application_status=st,
            submission_status=d.get("submission_status", "PENDING"),
            confirmation_id=d.get("confirmation_id"),
            confirmation_url=d.get("confirmation_url"),
            date_discovered=d.get("date_discovered", time.strftime("%Y-%m-%d")),
            date_shortlisted=d.get("date_shortlisted"),
            date_prepared=d.get("date_prepared"),
            date_applied=d.get("date_applied"),
            date_verified=d.get("date_verified"),
            last_updated=float(d.get("last_updated", time.time())),
            next_followup=d.get("next_followup") or d.get("follow_up_date"),
            priority=pri,
            notes=notes_val,
        )


# Alias ApplicationRecord to Application for clean backwards compatibility
ApplicationRecord = Application


@dataclass
class OfferCandidate:
    """Staged Offer record with conservative detection & human verification gating."""
    offer_id: str = field(default_factory=lambda: f"OFF-{uuid.uuid4().hex[:6].upper()}")
    application_id: str = ""
    company: str = ""
    role: str = ""
    salary: str = ""
    currency: str = "USD"
    bonus: str = ""
    benefits: List[str] = field(default_factory=list)
    location: str = ""
    work_mode: str = "Remote"      # Remote, Hybrid, Onsite
    joining_date: str = ""
    offer_date: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))
    expiry_date: str = ""
    status: OfferStatus = OfferStatus.OFFER_CANDIDATE
    confidence: float = 0.0
    evidence: str = ""
    conditions: List[str] = field(default_factory=list)
    documents_requested: List[str] = field(default_factory=list)
    contact_person: str = ""
    offer_url: str = ""
    attachment_names: List[str] = field(default_factory=list)
    fact_analysis: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, OfferStatus) else str(self.status)
        return d


@dataclass
class InterviewSchedule:
    """Deterministic Interview Schedule record with explicit timezone handling."""
    interview_id: str = field(default_factory=lambda: f"INT-{uuid.uuid4().hex[:6].upper()}")
    application_id: str = ""
    company: str = ""
    role: str = ""
    round: str = "Technical"        # Screening, Technical, System Design, HR, Final Round
    date: str = ""                  # YYYY-MM-DD
    time_str: str = ""              # HH:MM AM/PM
    timezone: str = ""              # IST, UTC, EST, PST, etc.
    utc_timestamp: Optional[float] = None
    local_timestamp: Optional[float] = None
    duration_minutes: int = 45
    meeting_url: str = ""
    platform: str = "Google Meet"   # Google Meet, Zoom, MS Teams, Phone
    interviewer: str = ""
    status: str = "SCHEDULED"       # REQUESTED, SCHEDULED, COMPLETED, RESCHEDULED, CANCELLED
    preparation_status: str = "PENDING"  # PENDING, GENERATED, REVIEWED
    calendar_event_id: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FollowupRecord:
    """Configurable Follow-up task with draft generation and approval gating."""
    followup_id: str = field(default_factory=lambda: f"FOL-{uuid.uuid4().hex[:6].upper()}")
    application_id: str = ""
    company: str = ""
    role: str = ""
    reason: str = "First follow-up after submission"
    due_date: str = ""              # YYYY-MM-DD
    priority: PriorityLevel = PriorityLevel.MEDIUM
    status: str = "PENDING"         # PENDING, DRAFT_GENERATED, SENT, SKIPPED, CANCELLED
    completed_date: Optional[str] = None
    draft_subject: str = ""
    draft_body: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["priority"] = self.priority.value if isinstance(self.priority, PriorityLevel) else str(self.priority)
        return d


@dataclass
class EmailEventRecord:
    """Processed Email Intelligence record with idempotency and privacy minimization."""
    email_event_id: str = field(default_factory=lambda: f"EML-{uuid.uuid4().hex[:8].upper()}")
    application_id: Optional[str] = None
    message_id_hash: str = ""
    provider: str = "gmail"         # gmail, outlook, imap
    sender: str = ""
    sender_domain: str = ""
    subject: str = ""
    received_time: str = ""
    classification: EmailClassification = EmailClassification.IRRELEVANT
    confidence: float = 0.0
    detected_event: str = ""
    action_taken: str = ""
    verification: str = "SUCCESS_VERIFIED"
    processed_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value if isinstance(self.classification, EmailClassification) else str(self.classification)
        return d


@dataclass
class CareerContact:
    """Recruiter & Hiring Manager contact associated with an application."""
    contact_id: str = field(default_factory=lambda: f"CNT-{uuid.uuid4().hex[:6].upper()}")
    application_id: Optional[str] = None
    company: str = ""
    name: str = ""
    title: str = "Recruiter"
    email: str = ""
    phone: str = ""
    linkedin_url: str = ""
    notes: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

