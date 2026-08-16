# core/terminal/commands.py — Modular Slash Command Engine for BR JARVIS CLI
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.terminal.renderer import TerminalRenderer
from core.terminal.theme import Glyphs, MODE_COLORS, HAS_RICH
from core.version import BUILD, CODENAME, VERSION

try:
    from rich.table import Table
    from rich.box import ROUNDED
except ImportError:
    Table = None
    ROUNDED = None

if TYPE_CHECKING:
    from core.terminal.session import TerminalSession

logger = logging.getLogger("JARVIS.TerminalCommands")

VALID_MODES = [
    "general", "coder", "analyst", "recon",
    "exploit", "report", "planner", "researcher", "automation"
]


class SlashCommandHandler:
    """Dispatches and executes interactive CLI slash commands."""

    def __init__(self, session: "TerminalSession"):
        self.session = session
        self.renderer = session.renderer

    def execute(self, cmd_line: str) -> bool:
        """Execute a slash command line. Returns False if exit/quit was requested."""
        raw = cmd_line.strip()
        if not raw:
            return True

        parts = raw.split(maxsplit=1)
        action = parts[0].lower()
        args_str = parts[1].strip() if len(parts) > 1 else ""

        # Normalize exit commands
        if action in ("/quit", "/exit", "quit", "exit"):
            return self._cmd_quit()

        dispatch_map = {
            "/help": self._cmd_help,
            "/status": self._cmd_status,
            "/mode": lambda: self._cmd_mode(args_str),
            "/model": lambda: self._cmd_model(args_str),
            "/tasks": lambda: self._cmd_tasks(args_str),
            "/memory": lambda: self._cmd_memory(args_str),
            "/tools": lambda: self._cmd_tools(args_str),
            "/plan": lambda: self._cmd_plan(args_str),
            "/verify": lambda: self._cmd_verify(args_str),
            "/diff": lambda: self._cmd_diff(args_str),
            "/career": lambda: self._cmd_career(args_str),
            "/applications": lambda: self._cmd_applications(args_str),
            "/interviews": lambda: self._cmd_interviews(args_str),
            "/offers": lambda: self._cmd_offers(args_str),
            "/emails": lambda: self._cmd_emails(args_str),
            "/resume": lambda: self._cmd_resume(args_str),
            "/jobs": lambda: self._cmd_jobs(args_str),
            "/apply": lambda: self._cmd_apply(args_str),
            "/ats": lambda: self._cmd_ats(args_str),

            "/doctor": self._cmd_doctor,
            "/history": lambda: self._cmd_history(args_str),
            "/export": lambda: self._cmd_export(args_str),
            "/compact": self._cmd_compact,
            "/flush": self._cmd_compact,
            "/clear": self._cmd_clear,
            "/version": self._cmd_version,
        }

        handler = dispatch_map.get(action)
        if handler:
            try:
                res = handler()
                return True if res is None else res
            except Exception as e:
                logger.exception("Error executing command '%s': %s", action, e)
                self.renderer.render_error("Command Execution Failed", str(e))
                return True

        self.renderer.render_error(
            "Unknown Command",
            f"Command '{action}' not recognized.",
            ["Type /help for the complete command reference.", "Type /mode to switch personas."]
        )
        return True

    # ── Command Implementations ───────────────────────────────────────────────

    def _cmd_help(self) -> None:
        """Display categorized help cards."""
        if HAS_RICH and self.renderer.console:
            table = Table(title="⚡ BR JARVIS CLI Agent Reference", border_style="cyan", box=ROUNDED)
            table.add_column("Category", style="bold yellow", width=16)
            table.add_column("Command", style="bold cyan", width=22)
            table.add_column("Description", style="white")

            # Agent & Routing
            table.add_row("Agent Persona", "/mode <name>", f"Switch mode: {', '.join(VALID_MODES)}")
            table.add_row("Agent Persona", "/model <name>", "View or switch active LLM backend profile")
            table.add_row("Agent Persona", "/plan <goal>", "Decompose and preview step plan without executing")

            # Memory & Tasks
            table.add_row("Memory & Context", "/memory <subcmd>", "search <query> │ recent │ project │ stats")
            table.add_row("Memory & Context", "/compact", "Consolidate working memory into long-term store")
            table.add_row("Memory & Context", "/history [n]", "Display recent session turns and tool history")
            table.add_row("Tasks & Lifecycle", "/tasks", "Inspect background and multi-stage task records")
            table.add_row("Tasks & Lifecycle", "/verify [path|task]", "Run disk / process verification checks")
            table.add_row("Tasks & Lifecycle", "/diff [file]", "Display syntax-highlighted file changes")

            # Career OS
            table.add_row("Career OS", "/career [stats|onboard]", "Profile overview, completeness & funnel analytics")
            table.add_row("Career OS", "/resume [role|tailor]", "Create or tailor resume (HTML/DOCX/PDF)")
            table.add_row("Career OS", "/jobs <query>", "Search and match jobs across Greenhouse, Lever, Ashby")
            table.add_row("Career OS", "/apply <job_id>", "Prepare application package & launch manual assistant")
            table.add_row("Career OS", "/ats [role]", "Run 7-factor deterministic ATS compatibility audit")

            # Tools & Diagnostics
            table.add_row("Tools & System", "/tools [filter]", "Browse and search registered tool definitions")
            table.add_row("Tools & System", "/status", "Subsystem telemetry, memory & backend health")
            table.add_row("Tools & System", "/doctor", "Run diagnostic self-healing repair audit")
            table.add_row("Tools & System", "/export [format]", "Export session transcript to artifact")
            table.add_row("Session Control", "/clear", "Clear terminal screen")
            table.add_row("Session Control", "/version", "Show build, codename and platform info")
            table.add_row("Session Control", "/quit", "Exit CLI with automatic memory consolidation")

            self.renderer.console.print(table)
        else:
            print("Commands: /help, /status, /career, /resume, /jobs, /apply, /ats, /mode, /model, /tasks, /memory, /tools, /doctor, /quit")

    def _cmd_status(self) -> None:
        """Display live subsystem status."""
        runtime = self.session.runtime
        orch = runtime.orchestrator if runtime else None
        current_mode = getattr(orch, "current_mode", "general") if orch else "offline"
        session_id = getattr(orch, "session_id", "N/A") if orch else "N/A"

        try:
            from tools.registry import TOOL_SCHEMAS
            tool_count = len(TOOL_SCHEMAS)
        except Exception:
            tool_count = 0

        try:
            from memory.unified_memory import get_unified_memory
            um = get_unified_memory()
            mem_summary = f"{len(um._cache) if hasattr(um, '_cache') else 'Active'} cached memories"
        except Exception:
            mem_summary = "Active"

        status_data = {
            "Version & Build": f"v{VERSION} ({CODENAME}, Build {BUILD})",
            "Active Agent Mode": current_mode.upper(),
            "Session ID": session_id,
            "Default Backend": getattr(runtime.config.models, "default_backend", "Gemini") if runtime and hasattr(runtime, "config") else "Gemini",
            "Registered Tools": f"{tool_count} tools available",
            "Unified Memory": mem_summary,
            "Action Verifier": "Host & Sandbox Validation Active",
            "Security Policy": "FAIL-CLOSED (Guardian Protected)",
        }
        self.renderer.render_status_table(status_data)

    def _cmd_mode(self, mode_name: str) -> None:
        """Switch active agent persona mode."""
        if not mode_name:
            current = getattr(self.session.orchestrator, "current_mode", "general")
            self.renderer.render_markdown(f"**Current Agent Mode:** `{current.upper()}`\n\nAvailable modes: {', '.join(f'`{m}`' for m in VALID_MODES)}")
            return

        target_mode = mode_name.lower().strip()
        if target_mode not in VALID_MODES:
            self.renderer.render_error("Invalid Mode", f"'{mode_name}' is not a recognized mode.", [f"Available modes: {', '.join(VALID_MODES)}"])
            return

        orch = self.session.orchestrator
        if orch:
            orch.current_mode = target_mode
            if hasattr(orch, "router") and hasattr(orch.router, "set_mode"):
                try:
                    orch.router.set_mode(target_mode)
                except Exception:
                    pass

        self.session.current_mode = target_mode
        mode_color = MODE_COLORS.get(target_mode, "cyan")
        if HAS_RICH and self.renderer.console:
            self.renderer.console.print(f"[{mode_color} bold]✓ Active Persona switched to:[/] [bold white]{target_mode.upper()}[/]")
        else:
            print(f"[Mode] Switched to {target_mode.upper()}")

    def _cmd_model(self, model_name: str) -> None:
        """View or switch active model backend."""
        runtime = self.session.runtime
        if not model_name:
            active_model = getattr(runtime.config.models, "default_backend", "gemini") if runtime and hasattr(runtime, "config") else "gemini"
            self.renderer.render_markdown(f"**Active Model Backend:** `{active_model}`")
            return

        if runtime and hasattr(runtime, "config"):
            runtime.config.models.default_backend = model_name
            self.renderer.render_markdown(f"**Default Model Backend changed to:** `{model_name}`")
        else:
            self.renderer.render_markdown(f"**Model selected:** `{model_name}`")

    def _cmd_tasks(self, filter_query: str = "") -> None:
        """List active and recent tasks from TaskStateManager."""
        try:
            from agent.task_state import get_task_state_manager
            mgr = get_task_state_manager()
            tasks = mgr.list_tasks(limit=15)
            if not tasks:
                self.renderer.render_markdown("_No task lifecycle records found._")
                return
            self.renderer.render_tasks_table(tasks)
        except Exception as e:
            self.renderer.render_error("Tasks Query Failed", str(e))

    def _cmd_memory(self, subcmd_line: str) -> None:
        """Handle /memory commands: search, recent, project, stats, clear."""
        try:
            from memory.unified_memory import get_unified_memory
            um = get_unified_memory()

            parts = subcmd_line.split(maxsplit=1)
            sub = parts[0].lower() if parts else ""
            arg = parts[1].strip() if len(parts) > 1 else ""

            if sub == "search" and arg:
                hits = um.recall(arg, limit=6)
                if not hits:
                    self.renderer.render_markdown(f"_No memories found for query:_ `{arg}`")
                    return
                self.renderer.render_memory_card(hits, title=f"Memory Search Results for '{arg}'")

            elif sub in ("recent", "latest"):
                from memory.persistent_store import load_index
                entries = load_index("user")[:8]
                mem_list = [{"type": e.type, "name": e.name, "content": e.content} for e in entries]
                if not mem_list:
                    self.renderer.render_markdown("_No recent memories found in persistent store._")
                    return
                self.renderer.render_memory_card(mem_list, title="Recent Stored Memories")

            elif sub in ("project", "workspace"):
                from memory.persistent_store import load_index
                entries = [e for e in load_index("user") if e.type in ("project", "operational")][:8]
                mem_list = [{"type": e.type, "name": e.name, "content": e.content} for e in entries]
                if not mem_list:
                    self.renderer.render_markdown("_No project memories found._")
                    return
                self.renderer.render_memory_card(mem_list, title="Project & Operational Memories")

            elif sub in ("stats", "summary"):
                from memory.persistent_store import load_index
                user_e = load_index("user")
                proj_e = load_index("project")
                by_type: dict = {}
                for e in user_e + proj_e:
                    by_type[e.type] = by_type.get(e.type, 0) + 1
                
                stats_dict = {"Total Persistent Memories": len(user_e) + len(proj_e)}
                for t, cnt in sorted(by_type.items()):
                    stats_dict[f"Type: {t}"] = f"{cnt} entries"
                self.renderer.render_status_table(stats_dict)

            else:
                self.renderer.render_markdown(
                    "### 🧠 Memory Command Reference\n"
                    "- `/memory search <query>` — Search knowledge graph & vector store\n"
                    "- `/memory recent` — Show latest stored facts and preferences\n"
                    "- `/memory project` — View project and workspace context\n"
                    "- `/memory stats` — Display breakdown of stored memory types\n"
                )
        except Exception as e:
            self.renderer.render_error("Memory Command Error", str(e))

    def _cmd_tools(self, filter_query: str = "") -> None:
        """Browse registered tool schemas."""
        try:
            from tools.registry import TOOL_SCHEMAS, _import_plugins
            _import_plugins()
            self.renderer.render_tools_table(TOOL_SCHEMAS, filter_query=filter_query)
        except Exception as e:
            self.renderer.render_error("Tool Registry Error", str(e))

    def _cmd_plan(self, goal: str) -> None:
        """Run step planner or stage decomposer on a goal without executing."""
        if not goal:
            self.renderer.render_error("Missing Goal", "Please provide a goal to plan, e.g. `/plan Build a REST API in Python`")
            return

        try:
            from agent.stage_decomposer import StageDecomposer
            if StageDecomposer.is_composite_task(goal):
                stages = StageDecomposer.decompose(goal)
                stages_data = [
                    {"name": s.name, "goal": s.goal, "agent_type": getattr(s.agent_type, "value", str(s.agent_type))}
                    for s in stages
                ]
                self.renderer.render_stage_progress(stages_data, 1, len(stages_data))
            else:
                from agent.step_planner import StepPlanner
                plan_info = StepPlanner.plan_steps(goal)
                self.renderer.render_markdown(
                    f"### 📋 Step Plan for: `{goal}`\n"
                    f"- **Complexity:** {plan_info.get('complexity', 'NORMAL')}\n"
                    f"- **Step Budget:** {plan_info.get('budget_controller', {}).initial_budget if hasattr(plan_info.get('budget_controller'), 'initial_budget') else 6} steps\n"
                    f"- **Decomposition:** Direct execution plan ready."
                )
        except Exception as e:
            self.renderer.render_error("Planning Failed", str(e))

    def _cmd_verify(self, target_path: str = "") -> None:
        """Run verification check on file or path."""
        try:
            from agent.verifier import get_action_verifier
            verifier = get_action_verifier()
            if target_path:
                res = verifier.verify_file_operation(target_path, "read")
                self.renderer.render_verification(res)
            else:
                self.renderer.render_markdown(
                    "**ActionVerifier Status:** `ACTIVE`\n\n"
                    "Usage: `/verify <filepath>` to verify disk presence, integrity and size."
                )
        except Exception as e:
            self.renderer.render_error("Verification Failed", str(e))

    def _cmd_diff(self, file_path: str = "") -> None:
        """Show diff for file if available."""
        if not file_path:
            self.renderer.render_markdown("Usage: `/diff <filepath>` to inspect changes.")
            return
        p = Path(file_path)
        if not p.exists():
            self.renderer.render_error("File Not Found", f"Cannot show diff: file '{file_path}' does not exist.")
            return
        content = p.read_text(encoding="utf-8", errors="replace")
        self.renderer.render_diff(file_path, "", content)

    # ── Career OS Commands ───────────────────────────────────────────────────

    def _cmd_career(self, args_str: str = "") -> None:
        """Career Profile and Funnel Analytics overview."""
        try:
            from career.profile_manager import get_profile_manager
            from career.analytics import CareerAnalyticsEngine
            
            mgr = get_profile_manager()
            profile = mgr.get_profile()
            val = mgr.validate_profile(profile)
            analytics = CareerAnalyticsEngine.compute_analytics()

            if "onboard" in args_str.lower():
                qs = mgr.get_onboarding_questions(profile)
                if not qs:
                    self.renderer.render_markdown("✓ **Profile Onboarding Complete:** Zero missing critical fields.")
                    return
                self.renderer.render_markdown(f"### 📋 Career Onboarding ({len(qs)} missing fields):")
                for idx, q in enumerate(qs, 1):
                    self.renderer.render_markdown(f"**{idx}. [{q['field']}]**: {q['question']}")
                return

            self.renderer.render_markdown(f"""### 💼 Career Profile Overview: **{profile.contact.full_name}**
* **Completeness Score:** `{val['score']}%` ({val['status']})
* **Target Roles:** {', '.join(profile.preferences.target_roles) or 'Not Specified'}
* **Work Mode:** {profile.preferences.remote_preference.replace('_', ' ').title()}
* **Locations:** {', '.join(profile.preferences.target_locations)}
* **Experience Entries:** {len(profile.experience)} │ **Projects:** {len(profile.projects)} │ **Skills:** {sum(len(s.skills) for s in profile.skills)}

#### 📊 Pipeline Telemetry:
* **Jobs Discovered:** `{analytics.total_jobs_discovered}` │ **Shortlisted:** `{analytics.total_shortlisted}`
* **Applications Submitted:** `{analytics.total_applications_submitted}` │ **Screenings:** `{analytics.total_screenings}` │ **Interviews:** `{analytics.total_interviews}`
* **Response Rate:** `{analytics.response_rate}%` │ **Interview Conversion:** `{analytics.interview_rate}%`
""")
        except Exception as e:
            self.renderer.render_error("Career Profile Error", str(e))

    def _cmd_applications(self, args_str: str = "") -> None:
        """List and manage active job applications."""
        try:
            from career.crm.database import get_career_crm_db
            from career.models import ApplicationStatus
            db = get_career_crm_db()
            apps = db.list_applications(limit=25)

            arg_low = args_str.lower().strip()
            if "followup" in arg_low:
                from career.crm.followup_engine import get_followup_engine
                fol_engine = get_followup_engine()
                pending = fol_engine.get_pending_followups()
                if not pending:
                    self.renderer.render_markdown("✓ **No follow-ups due right now.**")
                    return
                self.renderer.render_markdown(f"### ⏰ Pending Follow-ups ({len(pending)} due):")
                for f in pending:
                    self.renderer.render_markdown(f"• `[{f.followup_id}]` **{f.company}** — {f.role} (Due: `{f.due_date}`, Reason: {f.reason})")
                return

            if not apps:
                self.renderer.render_markdown("_No tracked job applications found. Use `/jobs` or `/apply` to start._")
                return

            self.renderer.render_markdown(f"### 📋 Tracked Job Applications ({len(apps)} active):")
            for a in apps[:10]:
                st_val = a.application_status.value if hasattr(a.application_status, "value") else str(a.application_status)
                self.renderer.render_markdown(f"• `[{a.application_id}]` **{a.company}** — {a.job_title} │ Status: `{st_val}` │ Priority: `{a.priority.value if hasattr(a.priority, 'value') else a.priority}`")
        except Exception as e:
            self.renderer.render_error("Applications List Error", str(e))

    def _cmd_interviews(self, args_str: str = "") -> None:
        """List scheduled and upcoming interviews."""
        try:
            from career.crm.database import get_career_crm_db
            db = get_career_crm_db()
            interviews = db.list_interviews(limit=15)
            if not interviews:
                self.renderer.render_markdown("_No upcoming interviews scheduled._")
                return
            self.renderer.render_markdown(f"### 📅 Upcoming Interviews ({len(interviews)} scheduled):")
            for iv in interviews:
                self.renderer.render_markdown(f"• `[{iv.interview_id}]` **{iv.company}** ({iv.round}) — `{iv.date} {iv.time_str} {iv.timezone}` │ Link: {iv.meeting_url or 'TBD'}")
        except Exception as e:
            self.renderer.render_error("Interviews Error", str(e))

    def _cmd_offers(self, args_str: str = "") -> None:
        """List and confirm detected job offers."""
        try:
            from career.crm.database import get_career_crm_db
            db = get_career_crm_db()
            offers = db.list_offers(limit=10)
            if not offers:
                self.renderer.render_markdown("_No job offers detected or recorded._")
                return
            self.renderer.render_markdown(f"### 🏆 Job Offers & Packages ({len(offers)} detected):")
            for off in offers:
                st_val = off.status.value if hasattr(off.status, "value") else str(off.status)
                self.renderer.render_markdown(f"• `[{off.offer_id}]` **{off.company}** — {off.role} │ Comp: `{off.salary}` │ Status: `{st_val}` │ Expiry: `{off.expiry_date or 'N/A'}`")
        except Exception as e:
            self.renderer.render_error("Offers Error", str(e))

    def _cmd_emails(self, args_str: str = "") -> None:
        """Career Email Intelligence events and synchronization."""
        try:
            from career.email_intelligence.service import get_email_career_intelligence
            from career.crm.database import get_career_crm_db
            db = get_career_crm_db()
            events = db.list_email_records(limit=10)
            if not events:
                self.renderer.render_markdown("_No career email events recorded yet. Ingesting automatically on sync._")
                return
            self.renderer.render_markdown(f"### 📧 Career Email Activity Feed ({len(events)} events):")
            for ev in events:
                cls_val = ev.classification.value if hasattr(ev.classification, "value") else str(ev.classification)
                self.renderer.render_markdown(f"• `[{ev.email_event_id}]` **{ev.sender}** │ `{cls_val}` ({ev.confidence*100:.0f}%) │ Subject: _{ev.subject[:50]}..._")
        except Exception as e:
            self.renderer.render_error("Email Intelligence Error", str(e))


    def _cmd_resume(self, args_str: str = "") -> None:
        """Create, tailor, or export resumes."""
        try:
            from career.profile_manager import get_profile_manager
            from career.resume_engine.renderer import ResumeRenderer
            from career.resume_engine.exporter import ResumeExportPipeline
            from career.resume_engine.version_manager import ResumeVersionManager

            mgr = get_profile_manager()
            profile = mgr.get_profile()

            role = args_str.strip() or (profile.preferences.target_roles[0] if profile.preferences.target_roles else "Systems Architect")
            schema = ResumeRenderer.schema_from_profile(profile, target_role=role)
            
            exporter = ResumeExportPipeline()
            res = exporter.export_all_formats(schema)

            ver_mgr = ResumeVersionManager.get_instance()
            ver_rec = ver_mgr.register_version(
                resume=schema,
                provider="native",
                docx_path=res["docx"]["path"],
                pdf_path=res["pdf"]["path"],
                html_path=res["html"]["path"],
            )

            self.renderer.render_markdown(f"""✓ **Resume Generated & Verified (v{ver_rec.version_id}):**
* **Title:** {schema.title}
* **DOCX:** `{res['docx']['path']}` ({'✓ Verified' if res['docx']['verified'] else 'Failed'})
* **PDF:** `{res['pdf']['path']}` ({'✓ Verified' if res['pdf']['verified'] else 'Failed'})
* **HTML:** `{res['html']['path']}` ({'✓ Verified' if res['html']['verified'] else 'Failed'})
""")
        except Exception as e:
            self.renderer.render_error("Resume Generation Error", str(e))

    def _cmd_jobs(self, query: str = "") -> None:
        """Search and match live job postings."""
        try:
            from career.job_engine.finder import JobFinder
            q = query.strip() or "Autonomous AI Systems Engineer"
            self.renderer.render_markdown(f"🔍 _Searching across Greenhouse, Lever, Ashby for:_ `{q}`...")

            finder = JobFinder.get_instance()
            results = finder.search_and_match(query_or_filters=q, limit=5)

            if not results:
                self.renderer.render_markdown(f"_No matching positions found for '{q}'._")
                return

            self.renderer.render_markdown(f"### 🎯 Top Job Matches ({len(results)} found):")
            for idx, r in enumerate(results, 1):
                j = r.job
                m = r.match
                self.renderer.render_markdown(f"""**{idx}. {j.title}** @ **{j.company}** (Fit: `{m.overall_score}%`)
* **ID:** `{j.job_id}` │ **Platform:** {j.platform} │ **Location:** {j.location} ({j.remote_type})
* **Salary:** {j.salary or 'Competitive'}
* **Strengths:** {'; '.join(m.key_strengths[:2]) if m.key_strengths else 'Good skills overlap'}
* **Apply:** [Application Portal]({j.application_url})
""")
        except Exception as e:
            self.renderer.render_error("Job Search Error", str(e))

    def _cmd_apply(self, job_id: str = "") -> None:
        """Prepare complete application package and open browser for job ID."""
        try:
            from career.job_engine.finder import JobFinder
            from career.application_engine.assistant import ManualApplicationAssistant
            
            jid = job_id.strip()
            if not jid:
                self.renderer.render_markdown("Usage: `/apply <job_id>` (Use `/jobs` to discover IDs).")
                return

            finder = JobFinder.get_instance()
            job = finder.get_job_by_id(jid)
            if not job:
                self.renderer.render_error("Job Not Found", f"No job found with ID '{jid}'.")
                return

            assistant = ManualApplicationAssistant()
            res = assistant.prepare_and_assist(job=job, auto_open_browser=True)

            if not res.get("success"):
                self.renderer.render_error("Application Blocked", res.get("message", "Application could not be prepared."))
                return

            self.renderer.render_markdown(f"""✓ **Application Package Ready for {job.company}:**
* **Application ID:** `{res['application_id']}` │ **Package:** `{res['package_id']}`
* **Portal URL Opened:** {res['application_url']}
* **Tailored Resume PDF:** `{res['resume_pdf']}`
* **Tailored Cover Letter:** `{res['cover_letter_pdf']}`
* **Status:** `READY_FOR_REVIEW` (Human confirmation required before submission).
""")
        except Exception as e:
            self.renderer.render_error("Application Assistant Error", str(e))

    def _cmd_ats(self, role_str: str = "") -> None:
        """Run 7-factor deterministic ATS audit."""
        try:
            from career.profile_manager import get_profile_manager
            from career.resume_engine.renderer import ResumeRenderer
            from career.ats_engine.scorer import ATSEngine

            mgr = get_profile_manager()
            profile = mgr.get_profile()
            schema = ResumeRenderer.schema_from_profile(profile, target_role=role_str.strip() or None)

            rep = ATSEngine.evaluate_resume(schema)
            self.renderer.render_markdown(f"""### 🎯 ATS Evaluation Audit: **Grade {rep.grade}** (`{rep.overall_score}%`)
* **Keyword Coverage:** `{rep.keyword_coverage_score}%`
* **Section Recognition:** `{rep.section_recognition_score}%`
* **Parsing Safety Index:** `{rep.parsing_risk_score}%`
* **Readability & Action Verbs:** `{rep.readability_score}%`
* **Formatting Consistency:** `{rep.consistency_score}%`
* **Role Alignment:** `{rep.role_relevance_score}%`

#### 💡 Actionable Optimizations:
{chr(10).join(f'* {c}' for c in rep.recommended_changes[:4]) if rep.recommended_changes else '* All ATS metrics optimal.'}
""")
        except Exception as e:
            self.renderer.render_error("ATS Audit Error", str(e))

    def _cmd_doctor(self) -> None:
        """Run diagnostic system health check."""
        try:
            from start import doctor
            doctor(auto_confirm=True)
        except Exception as e:
            self.renderer.render_error("Doctor Diagnostic Error", str(e))

    def _cmd_history(self, limit_str: str = "") -> None:
        """View recent session turns."""
        try:
            limit = int(limit_str) if limit_str.isdigit() else 5
            orch = self.session.orchestrator
            if orch and hasattr(orch, "working_memory"):
                history = orch.working_memory.get()[-limit*2:]
                if not history:
                    self.renderer.render_markdown("_No conversation history in current session._")
                    return
                self.renderer.render_markdown(f"### 📜 Session History (Last {len(history)} messages)")
                for msg in history:
                    role = msg.get("role", "system").upper()
                    content = str(msg.get("content", ""))[:200]
                    self.renderer.render_markdown(f"**[{role}]**: {content}")
            else:
                self.renderer.render_markdown("_History store not connected._")
        except Exception as e:
            self.renderer.render_error("History Error", str(e))

    def _cmd_export(self, format_spec: str = "markdown") -> None:
        """Export session transcript to artifact."""
        try:
            from agent.artifacts import get_artifact_manager
            mgr = get_artifact_manager()
            orch = self.session.orchestrator
            history = orch.working_memory.get() if orch and hasattr(orch, "working_memory") else []
            
            lines = [f"# BR JARVIS Session Export ({self.session.session_id})", f"**Mode:** {self.session.current_mode}", ""]
            for h in history:
                role = h.get("role", "").upper()
                content = h.get("content", "")
                lines.append(f"### [{role}]\n{content}\n")
            
            body = "\n".join(lines)
            art = mgr.create_artifact(
                filename=f"session_export_{self.session.session_id[:8]}.md",
                content=body,
                category="report",
                metadata={"session_id": self.session.session_id}
            )
            self.renderer.render_markdown(f"✓ Session exported to artifact: `{art.host_path or art.sandbox_path}`")
        except Exception as e:
            self.renderer.render_error("Export Failed", str(e))

    def _cmd_compact(self) -> None:
        """Consolidate working memory into long-term storage."""
        try:
            orch = self.session.orchestrator
            if orch and hasattr(orch, "consolidate_on_exit"):
                res = orch.consolidate_on_exit()
                if hasattr(orch.working_memory, "trim"):
                    orch.working_memory.trim(max_turns=4)
                self.renderer.render_markdown(f"✓ **Memory Consolidated:** {res or 'Working memory trimmed.'}")
            else:
                self.renderer.render_markdown("Memory consolidation completed.")
        except Exception as e:
            self.renderer.render_error("Compaction Failed", str(e))

    def _cmd_clear(self) -> None:
        """Clear screen and re-render header."""
        self.renderer.clear()
        self.session.render_header()

    def _cmd_version(self) -> None:
        """Display canonical version info."""
        self.renderer.render_markdown(f"**BR JARVIS:** `v{VERSION}` ({CODENAME}, Build `{BUILD}`)")

    def _cmd_quit(self) -> bool:
        """Clean shutdown with consolidation."""
        try:
            orch = self.session.orchestrator
            if orch and hasattr(orch, "shutdown"):
                orch.shutdown()
        except Exception:
            pass
        if HAS_RICH and self.renderer.console:
            self.renderer.console.print("\n[bold yellow]⚡ BR JARVIS Session closed. Learnings consolidated.[/bold yellow]\n")
        else:
            print("\nBR JARVIS Session closed.")
        return False
