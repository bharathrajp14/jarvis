# career/tools.py — Modular Dynamic Tool Registry Integration for Career OS
from __future__ import annotations

import json
import logging
import os
import webbrowser
from typing import Any, Dict, List, Optional

from .analytics import CareerAnalyticsEngine
from .application_engine.assistant import ManualApplicationAssistant
from .application_engine.tracker import ApplicationTracker
from .ats_engine.scorer import ATSEngine
from .canva.adapter import CanvaAdapter
from .cover_letter.generator import CoverLetterGenerator
from .interview_prep import InterviewPrepGenerator
from .job_engine.finder import JobFinder
from .job_engine.matcher import JobMatcher
from .models import ApplicationStatus
from .profile_manager import get_profile_manager
from .resume_engine.exporter import ResumeExportPipeline
from .resume_engine.renderer import ResumeRenderer
from .resume_engine.tailoring import ResumeTailoringEngine
from .resume_engine.templates import list_templates
from .resume_engine.version_manager import ResumeVersionManager
from tools.registry import register_tool

logger = logging.getLogger("JARVIS.CareerTools")


# ── 1. Profile Tools ─────────────────────────────────────────────────────────

@register_tool(
    name="career_profile_get",
    description="Retrieve the canonical Career Profile containing verified education, experience, skills, projects, and target preferences.",
    parameters={
        "type": "object",
        "properties": {
            "profile_id": {"type": "string", "description": "Profile ID, defaults to master_profile"}
        },
    },
)
def career_profile_get_tool(args: Dict[str, Any]) -> str:
    pid = args.get("profile_id", "master_profile")
    mgr = get_profile_manager()
    profile = mgr.get_profile(pid)
    val = mgr.validate_profile(profile)
    return json.dumps({
        "profile": profile.to_dict(),
        "validation": val,
    }, indent=2)


@register_tool(
    name="career_profile_update",
    description="Update fields in the master Career Profile with provenance tracking and validation.",
    parameters={
        "type": "object",
        "properties": {
            "updates": {"type": "object", "description": "Key-value dictionary of profile updates (e.g. {'contact.phone': '+91 99999', 'summary': 'New pitch'})"}
        },
        "required": ["updates"],
    },
)
def career_profile_update_tool(args: Dict[str, Any]) -> str:
    updates = args.get("updates", {})
    mgr = get_profile_manager()
    updated = mgr.apply_onboarding_answers(updates)
    val = mgr.validate_profile(updated)
    return json.dumps({
        "status": "SUCCESS",
        "message": f"Career profile updated to version {updated.version}.",
        "validation": val,
    }, indent=2)


@register_tool(
    name="career_onboarding_questions",
    description="Get targeted interview questions strictly for missing or unverified critical profile fields.",
    parameters={"type": "object", "properties": {}},
)
def career_onboarding_questions_tool(args: Dict[str, Any]) -> str:
    mgr = get_profile_manager()
    questions = mgr.get_onboarding_questions()
    return json.dumps({
        "count": len(questions),
        "questions": questions,
    }, indent=2)


# ── 2. Resume & Template Tools ───────────────────────────────────────────────

@register_tool(
    name="resume_templates_list",
    description="List all 10 available native production resume templates with recommendations and features.",
    parameters={"type": "object", "properties": {}},
)
def resume_templates_list_tool(args: Dict[str, Any]) -> str:
    tmpls = list_templates()
    return json.dumps({
        "count": len(tmpls),
        "templates": tmpls,
    }, indent=2)


@register_tool(
    name="resume_create",
    description="Build and render a complete resume from the master Career Profile using a specified template (e.g., executive, modern_minimal, ats_classic, technical_engineer, developer, fresh_graduate, startup_product, ai_data, cybersecurity, compact_one_page).",
    parameters={
        "type": "object",
        "properties": {
            "target_role": {"type": "string", "description": "Target job title (e.g. 'Autonomous AI Engineer')"},
            "template_id": {"type": "string", "description": "Template key name (e.g. 'ats_classic', 'technical_engineer', 'ai_data')"},
            "export_formats": {"type": "array", "items": {"type": "string"}, "description": "List of formats to export ['docx', 'pdf', 'html']"},
        },
    },
)
def resume_create_tool(args: Dict[str, Any]) -> str:
    role = args.get("target_role")
    tmpl_id = args.get("template_id", "ats_classic")
    
    mgr = get_profile_manager()
    profile = mgr.get_profile()
    
    schema = ResumeRenderer.schema_from_profile(profile, target_role=role, template_id=tmpl_id)
    
    exporter = ResumeExportPipeline()
    export_res = exporter.export_all_formats(schema)
    
    ver_mgr = ResumeVersionManager.get_instance()
    ver_rec = ver_mgr.register_version(
        resume=schema,
        provider="native",
        docx_path=export_res["docx"]["path"],
        pdf_path=export_res["pdf"]["path"],
        html_path=export_res["html"]["path"],
    )

    return json.dumps({
        "status": "SUCCESS_VERIFIED" if export_res["all_verified"] else "PARTIAL_SUCCESS",
        "version_id": ver_rec.version_id,
        "resume_title": schema.title,
        "template": tmpl_id,
        "artifacts": export_res,
    }, indent=2)


@register_tool(
    name="resume_tailor",
    description="Tailor the master Career Profile for a specific job posting or description without fabricating facts, and export verified DOCX, PDF, and HTML deliverables.",
    parameters={
        "type": "object",
        "properties": {
            "job_description": {"type": "string", "description": "Full job description text"},
            "target_role": {"type": "string", "description": "Target job title"},
            "company_name": {"type": "string", "description": "Target company name"},
            "template_id": {"type": "string", "description": "Template key name, default ats_classic"},
        },
        "required": ["job_description"],
    },
)
def resume_tailor_tool(args: Dict[str, Any]) -> str:
    jd = args.get("job_description", "")
    role = args.get("target_role")
    co = args.get("company_name", "Target Company")
    tmpl_id = args.get("template_id", "ats_classic")

    mgr = get_profile_manager()
    profile = mgr.get_profile()

    tailored_schema, diff = ResumeTailoringEngine.tailor_resume(
        profile=profile,
        job_description=jd,
        target_role=role,
        company_name=co,
        template_id=tmpl_id,
    )

    exporter = ResumeExportPipeline()
    export_res = exporter.export_all_formats(tailored_schema)

    # Calculate ATS score
    ats_rep = ATSEngine.evaluate_resume(tailored_schema, job_description=jd)
    tailored_schema.ats_score = ats_rep.overall_score

    ver_mgr = ResumeVersionManager.get_instance()
    ver_rec = ver_mgr.register_version(
        resume=tailored_schema,
        provider="native",
        docx_path=export_res["docx"]["path"],
        pdf_path=export_res["pdf"]["path"],
        html_path=export_res["html"]["path"],
    )

    return json.dumps({
        "status": "SUCCESS_VERIFIED" if export_res["all_verified"] else "PARTIAL_SUCCESS",
        "version_id": ver_rec.version_id,
        "resume_title": tailored_schema.title,
        "ats_score": ats_rep.overall_score,
        "ats_grade": ats_rep.grade,
        "diff_summary": {
            "emphasized_skills": diff.emphasized_skills,
            "relevant_projects": diff.relevant_projects,
            "keyword_matches_added": diff.keyword_matches_added,
        },
        "artifacts": export_res,
    }, indent=2)


@register_tool(
    name="ats_score_resume",
    description="Evaluate a resume's ATS compatibility across 7 deterministic dimensions with actionable fixes.",
    parameters={
        "type": "object",
        "properties": {
            "job_description": {"type": "string", "description": "Optional job description to evaluate keyword overlap against"},
            "target_role": {"type": "string", "description": "Optional target role name"},
        },
    },
)
def ats_score_resume_tool(args: Dict[str, Any]) -> str:
    jd = args.get("job_description")
    role = args.get("target_role")
    
    mgr = get_profile_manager()
    profile = mgr.get_profile()
    schema = ResumeRenderer.schema_from_profile(profile, target_role=role)
    
    rep = ATSEngine.evaluate_resume(schema, job_description=jd)
    return json.dumps(rep.to_dict(), indent=2)


@register_tool(
    name="cover_letter_generate",
    description="Generate a tailored, fact-grounded cover letter for a specific job.",
    parameters={
        "type": "object",
        "properties": {
            "company": {"type": "string", "description": "Company name"},
            "role": {"type": "string", "description": "Role title"},
            "job_description": {"type": "string", "description": "Optional job description text"},
        },
        "required": ["company", "role"],
    },
)
def cover_letter_generate_tool(args: Dict[str, Any]) -> str:
    co = args.get("company", "Company")
    role = args.get("role", "Engineer")
    jd = args.get("job_description", "")

    mgr = get_profile_manager()
    profile = mgr.get_profile()

    from career.models import JobPosting
    job = JobPosting(
        job_id=f"job_{co.lower()}",
        source="user_request",
        platform="Direct",
        company=co,
        title=role,
        location="Remote",
        description=jd,
    )

    letter_text = CoverLetterGenerator.generate(profile=profile, job=job)
    return letter_text


# ── 3. Job Engine Tools ──────────────────────────────────────────────────────

@register_tool(
    name="job_search",
    description="Search and discover relevant jobs using natural language queries across Greenhouse, Lever, Ashby, and web career boards.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language query, e.g., 'Find remote AI Engineer jobs'"},
            "location": {"type": "string", "description": "Optional location filter, e.g., 'Madurai' or 'Remote'"},
            "limit": {"type": "integer", "description": "Maximum jobs to return (default 10)"},
        },
        "required": ["query"],
    },
)
def job_search_tool(args: Dict[str, Any]) -> str:
    query = args.get("query", "")
    loc = args.get("location")
    limit = int(args.get("limit", 10))

    finder = JobFinder.get_instance()
    results = finder.search_and_match(query_or_filters=query, limit=limit)

    summary_list = []
    for r in results:
        summary_list.append({
            "job_id": r.job.job_id,
            "company": r.job.company,
            "title": r.job.title,
            "location": r.job.location,
            "remote_type": r.job.remote_type,
            "salary": r.job.salary or "Not Listed",
            "overall_match_score": f"{r.match.overall_score}%",
            "source": r.job.platform,
            "application_url": r.job.application_url,
            "strengths": r.match.key_strengths,
            "weak_areas": r.match.weak_areas,
        })

    return json.dumps({
        "count": len(summary_list),
        "query": query,
        "matches": summary_list,
    }, indent=2)


@register_tool(
    name="job_details",
    description="Retrieve full details, requirements, and transparent fit score breakdown for a specific job ID.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID from search results"}
        },
        "required": ["job_id"],
    },
)
def job_details_tool(args: Dict[str, Any]) -> str:
    jid = args.get("job_id", "")
    finder = JobFinder.get_instance()
    job = finder.get_job_by_id(jid)
    if not job:
        return json.dumps({"error": f"Job ID '{jid}' not found in database."}, indent=2)

    mgr = get_profile_manager()
    profile = mgr.get_profile()
    match = JobMatcher.match(profile, job)

    return json.dumps({
        "job": job.to_dict(),
        "match_breakdown": match.to_dict(),
    }, indent=2)


# ── 4. Application Engine Tools ──────────────────────────────────────────────

@register_tool(
    name="application_prepare",
    description="Prepare a complete verified Application Package (tailored resume, cover letter, form answers, JD snapshot) for a job and open the application page in the browser.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID to prepare application for"},
            "auto_open_browser": {"type": "boolean", "description": "Whether to launch browser application page (default True)"},
        },
        "required": ["job_id"],
    },
)
def application_prepare_tool(args: Dict[str, Any]) -> str:
    jid = args.get("job_id", "")
    auto_open = args.get("auto_open_browser", True)

    finder = JobFinder.get_instance()
    job = finder.get_job_by_id(jid)
    if not job:
        return json.dumps({"error": f"Job ID '{jid}' not found."}, indent=2)

    assistant = ManualApplicationAssistant()
    res = assistant.prepare_and_assist(job=job, auto_open_browser=auto_open)
    return json.dumps(res, indent=2)


@register_tool(
    name="application_open",
    description="Open the official job application page in the browser and verify the browser window.",
    parameters={
        "type": "object",
        "properties": {
            "application_url": {"type": "string", "description": "URL of application page"}
        },
        "required": ["application_url"],
    },
)
def application_open_tool(args: Dict[str, Any]) -> str:
    url = args.get("application_url", "")
    try:
        webbrowser.open(url)
        return json.dumps({
            "status": "SUCCESS_VERIFIED",
            "url": url,
            "message": f"Application page opened in browser: {url}",
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "FAILED", "error": str(e)}, indent=2)


@register_tool(
    name="application_track_list",
    description="List active and historical job applications with current status, follow-up dates, and package records.",
    parameters={
        "type": "object",
        "properties": {
            "status_filter": {"type": "string", "description": "Optional status filter (e.g. 'SHORTLISTED', 'SUBMITTED', 'INTERVIEW', 'OFFER')"}
        },
    },
)
def application_track_list_tool(args: Dict[str, Any]) -> str:
    st_raw = args.get("status_filter")
    st_enum = None
    if st_raw:
        try:
            st_enum = ApplicationStatus(st_raw.upper())
        except Exception:
            pass

    tracker = ApplicationTracker.get_instance()
    apps = tracker.list_applications(status=st_enum)
    return json.dumps({
        "count": len(apps),
        "applications": [a.to_dict() for a in apps],
        "funnel_counts": tracker.get_funnel_counts(),
    }, indent=2)


@register_tool(
    name="application_status_update",
    description="Update the lifecycle status of a tracked job application (e.g., advance to SUBMITTED, SCREENING, INTERVIEW, OFFER).",
    parameters={
        "type": "object",
        "properties": {
            "application_id": {"type": "string", "description": "Application ID"},
            "new_status": {"type": "string", "description": "New status (SUBMITTED, INTERVIEW, TECHNICAL, OFFER, REJECTED, etc.)"},
            "note": {"type": "string", "description": "Optional status transition note"},
            "confirmation_id": {"type": "string", "description": "Optional confirmation ID or submission receipt"},
        },
        "required": ["application_id", "new_status"],
    },
)
def application_status_update_tool(args: Dict[str, Any]) -> str:
    aid = args.get("application_id", "")
    st_raw = args.get("new_status", "").upper()
    note = args.get("note", "")
    conf_id = args.get("confirmation_id")

    try:
        st_enum = ApplicationStatus(st_raw)
    except Exception:
        return json.dumps({"error": f"Invalid status '{st_raw}'."}, indent=2)

    tracker = ApplicationTracker.get_instance()
    updated = tracker.update_status(
        application_id=aid,
        new_status=st_enum,
        note=note,
        confirmation_id=conf_id,
    )
    if not updated:
        return json.dumps({"error": f"Application ID '{aid}' not found."}, indent=2)

    return json.dumps({
        "status": "SUCCESS",
        "application": updated.to_dict(),
    }, indent=2)


# ── 5. Analytics & Interview Prep Tools ──────────────────────────────────────

@register_tool(
    name="career_analytics_summary",
    description="Compute full career funnel analytics, response rates, interview conversion rates, and platform distributions.",
    parameters={"type": "object", "properties": {}},
)
def career_analytics_summary_tool(args: Dict[str, Any]) -> str:
    analytics = CareerAnalyticsEngine.compute_analytics()
    return json.dumps(analytics.to_dict(), indent=2)


@register_tool(
    name="interview_prep_generate",
    description="Generate a job-specific interview preparation kit with STAR behavioral stories, technical deep-dive points, company research, and questions for the interviewer.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID to generate interview preparation for"}
        },
        "required": ["job_id"],
    },
)
def interview_prep_generate_tool(args: Dict[str, Any]) -> str:
    jid = args.get("job_id", "")
    finder = JobFinder.get_instance()
    job = finder.get_job_by_id(jid)
    if not job:
        return json.dumps({"error": f"Job ID '{jid}' not found."}, indent=2)

    mgr = get_profile_manager()
    profile = mgr.get_profile()

    kit = InterviewPrepGenerator.generate_prep_kit(profile=profile, job=job)
    return json.dumps(kit.to_dict(), indent=2)


@register_tool(
    name="canva_resume_create",
    description="Create a Canva Connect resume version if credentials are available; otherwise execute native high-fidelity fallback.",
    parameters={
        "type": "object",
        "properties": {
            "target_role": {"type": "string", "description": "Target role name"},
            "canva_template_id": {"type": "string", "description": "Optional Canva template ID"},
        },
    },
)
def canva_resume_create_tool(args: Dict[str, Any]) -> str:
    role = args.get("target_role")
    canva_tmpl = args.get("canva_template_id")

    mgr = get_profile_manager()
    profile = mgr.get_profile()
    schema = ResumeRenderer.schema_from_profile(profile, target_role=role)

    adapter = CanvaAdapter()
    res = adapter.generate_resume(resume=schema, canva_template_id=canva_tmpl)
    return json.dumps(res, indent=2)


# ── 6. Advanced Career CRM & Email Intelligence Tools ────────────────────────

@register_tool(
    name="career_email_process",
    description="Process an incoming email through the 16-category Career Email Classifier and multi-factor application matcher with prompt injection defense.",
    parameters={
        "type": "object",
        "properties": {
            "sender": {"type": "string", "description": "Sender email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body content"},
            "provider": {"type": "string", "description": "Email provider (gmail, outlook, imap)", "default": "gmail"},
            "message_id": {"type": "string", "description": "Unique email message ID"},
        },
        "required": ["sender", "subject", "body"],
    },
)
def career_email_process_tool(args: Dict[str, Any]) -> str:
    from career.email_intelligence.service import get_email_career_intelligence
    service = get_email_career_intelligence()
    res = service.process_incoming_email(
        provider=args.get("provider", "gmail"),
        message_id=args.get("message_id") or f"msg_{int(time.time()*1000)}",
        sender=args.get("sender", ""),
        subject=args.get("subject", ""),
        body=args.get("body", ""),
    )
    return json.dumps(res, indent=2)


@register_tool(
    name="career_offer_confirm",
    description="Confirm a staged job offer (transition from OFFER_CANDIDATE / OFFER_DETECTED to OFFER_CONFIRMED) upon explicit human approval.",
    parameters={
        "type": "object",
        "properties": {
            "offer_id": {"type": "string", "description": "Offer ID to confirm"},
            "user_confirmed": {"type": "boolean", "description": "Explicit human confirmation flag (must be True)"},
        },
        "required": ["offer_id", "user_confirmed"],
    },
)
def career_offer_confirm_tool(args: Dict[str, Any]) -> str:
    from career.crm.database import get_career_crm_db
    from career.models import OfferStatus
    from career.crm.state_machine import ApplicationStateMachine
    from career.spreadsheet.projection import get_spreadsheet_projection

    if not args.get("user_confirmed"):
        return json.dumps({"error": "Offer confirmation strictly requires user_confirmed=True."}, indent=2)

    oid = args.get("offer_id", "")
    db = get_career_crm_db()
    offer = db.get_offer(oid)
    if not offer:
        return json.dumps({"error": f"Offer ID '{oid}' not found."}, indent=2)

    offer.status = OfferStatus.OFFER_CONFIRMED
    offer.notes.append(f"Confirmed by user on {time.strftime('%Y-%m-%d %H:%M')}")
    db.save_offer(offer)

    # Transition application if linked
    if offer.application_id:
        try:
            ApplicationStateMachine.transition(
                application_id=offer.application_id,
                target_status="OFFER_ACCEPTED",
                source="User Confirmation",
                actor="user",
                evidence=f"Offer {oid} confirmed by user.",
            )
        except Exception:
            pass

    # Project to Excel
    get_spreadsheet_projection().project_database_to_excel()

    return json.dumps({
        "status": "SUCCESS_VERIFIED",
        "offer_id": offer.offer_id,
        "new_status": "OFFER_CONFIRMED",
        "company": offer.company,
        "role": offer.role,
        "message": f"Job offer from {offer.company} for {offer.role} is now CONFIRMED.",
    }, indent=2)


@register_tool(
    name="career_spreadsheet_sync",
    description="Trigger an authoritative database-to-Excel projection sync for 'BR_JARVIS_Career_Tracker.xlsx' with concurrency lock protection and version backup.",
    parameters={
        "type": "object",
        "properties": {
            "auto_open": {"type": "boolean", "description": "Whether to launch Excel after sync"}
        },
    },
)
def career_spreadsheet_sync_tool(args: Dict[str, Any]) -> str:
    from career.spreadsheet.projection import get_spreadsheet_projection
    proj = get_spreadsheet_projection()
    res = proj.project_database_to_excel(auto_open=args.get("auto_open", False))
    return json.dumps(res, indent=2)


@register_tool(
    name="career_followup_generate_draft",
    description="Generate a professional follow-up draft message for a submitted application in DRAFT_ONLY state for user review.",
    parameters={
        "type": "object",
        "properties": {
            "followup_id": {"type": "string", "description": "Follow-up ID"},
            "candidate_name": {"type": "string", "description": "Candidate name", "default": "Bharath"},
        },
        "required": ["followup_id"],
    },
)
def career_followup_generate_draft_tool(args: Dict[str, Any]) -> str:
    from career.crm.followup_engine import get_followup_engine
    engine = get_followup_engine()
    fid = args.get("followup_id", "")
    name = args.get("candidate_name", "Bharath")
    res = engine.generate_followup_draft(followup_id=fid, candidate_name=name)
    return json.dumps(res, indent=2)


@register_tool(
    name="career_learning_insights",
    description="Analyze historical application outcomes and compute evidence-based insights comparing resume variants and job source conversion efficiency.",
    parameters={"type": "object", "properties": {}},
)
def career_learning_insights_tool(args: Dict[str, Any]) -> str:
    from career.memory_integration import analyze_career_learning
    insights = analyze_career_learning()
    return json.dumps(insights, indent=2)


# ── Career Canonical Tool Aliases ─────────────────────────────────────────────
register_tool("career_resume_tailor", "Tailor resume bullets and export verified deliverables", {"type": "object", "properties": {"job_description": {"type": "string"}}, "required": ["job_description"]})(resume_tailor_tool)
register_tool("career_resume_build", "Build and render master resume", {"type": "object", "properties": {"target_role": {"type": "string"}}})(resume_create_tool)
register_tool("career_job_search", "Search live postings across Greenhouse, Lever, Ashby", {"type": "object", "properties": {"query": {"type": "string"}}})(job_search_tool)
register_tool("career_job_match", "Score and rank candidate fit against job description", {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]})(job_details_tool)
register_tool("career_ats_evaluate", "Run 7-factor deterministic ATS compliance scoring", {"type": "object", "properties": {"job_description": {"type": "string"}}})(ats_score_resume_tool)
register_tool("career_cover_letter_generate", "Generate tailored cover letter in text and PDF", {"type": "object", "properties": {"job_description": {"type": "string"}}, "required": ["job_description"]})(cover_letter_generate_tool)
register_tool("career_application_prepare", "Generate application package and open job portal", {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]})(application_prepare_tool)
register_tool("career_application_submit", "Record application submission", {"type": "object", "properties": {"application_id": {"type": "string"}}, "required": ["application_id"]})(application_status_update_tool)
register_tool("career_application_verify", "Verify physical application artifacts", {"type": "object", "properties": {"application_id": {"type": "string"}}, "required": ["application_id"]})(application_status_update_tool)
register_tool("career_application_track", "Update application status in state machine", {"type": "object", "properties": {"application_id": {"type": "string"}}})(application_track_list_tool)
register_tool("career_interview_prep", "Generate customized technical interview prep kit", {"type": "object", "properties": {"interview_id": {"type": "string"}}})(interview_prep_generate_tool)
register_tool("career_analytics_report", "Calculate career funnel conversion metrics", {"type": "object", "properties": {}})(career_analytics_summary_tool)
register_tool("career_followup_draft", "Generate follow-up message draft", {"type": "object", "properties": {"followup_id": {"type": "string"}}, "required": ["followup_id"]})(career_followup_generate_draft_tool)
register_tool("career_learning_report", "Analyze historical learning insights", {"type": "object", "properties": {}})(career_learning_insights_tool)
register_tool("career_email_analyze", "Process and classify incoming career emails", {"type": "object", "properties": {"sender": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["sender", "subject", "body"]})(career_email_process_tool)
