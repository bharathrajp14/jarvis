# tools/registry.py — JARVIS MK37 Universal Tool Registry
"""
Universal tool registry and executor for JARVIS MK37.
Uses a decorator-based plugin system to register and execute tools.
"""
from __future__ import annotations

import asyncio
import json
import logging
import traceback
import sys
import importlib
import re
import threading
from pathlib import Path
from typing import Callable, Any

logger = logging.getLogger("JARVIS.ToolRegistry")

# Global registry mappings
TOOL_SCHEMAS: list[dict] = []
TOOL_REGISTRY: dict[str, Callable[[dict], Any]] = {}
_REGISTRATION_ERRORS: dict[str, str] = {}

# Thread-safe lock protecting TOOL_SCHEMAS and TOOL_REGISTRY mutations
_REGISTRY_LOCK = threading.RLock()

def get_tool_registry() -> dict[str, Callable[[dict], Any]]:
    """Return dictionary of all registered tools."""
    return TOOL_REGISTRY

# Cache references
_orchestrator_ref: Any = None


_TOOL_CALL_CODEBLOCK_RE = re.compile(r'```tool_call\s*\n\s*(\{.*?\})\s*\n\s*```', re.DOTALL)
_TOOL_CALL_JSON_RE = re.compile(r'(\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{.*?\}\s*\})', re.DOTALL)
_CODE_JSON_RE = re.compile(r'(\{\s*"code"\s*:\s*"[^"]+"\s*,\s*"lang"\s*:\s*"[^"]+"\s*\})', re.DOTALL)
_OSS_MESSAGE_RE = re.compile(r'<\|message\|>\s*(\{.*?\})', re.DOTALL)
_OSS_TOOL_HINT_RE = re.compile(r'(?:to|call)=?([\w\.\-]+)')


def register_tool(
    name: str,
    description: str,
    parameters: dict | None = None,
    category: str = "general",
    risk_level: str = "low",
    permission_required: str = "PUBLIC_READ",
    approval_required: bool = False,
    is_read_only: bool = False,
    idempotent: bool = True,
    timeout_sec: float = 30.0,
    verification_strategy: str = "NONE",
    **kwargs: Any,
) -> Callable:
    """Decorator to register a tool function in the JARVIS registry and ToolRuntime (thread-safe)."""
    def decorator(func: Callable[[dict], Any]) -> Callable[[dict], Any]:
        schema = {
            "name": name,
            "description": description,
            "parameters": parameters or {}
        }
        with _REGISTRY_LOCK:
            existing = TOOL_REGISTRY.get(name)
            if existing is not None and existing is not func:
                existing_name = getattr(existing, "__qualname__", str(existing))
                # If replacing a lazy wrapper with the real native implementation, log at debug
                if "_lazy_wrapper" in existing_name or "_lazy_register_tool" in existing_name:
                    logger.debug(f"[ToolRegistry] Resolved lazy tool '{name}' -> {func.__module__}.{func.__qualname__}")
                else:
                    same_module = getattr(existing, '__module__', None) == getattr(func, '__module__', None)
                    same_name = getattr(existing, '__qualname__', None) == getattr(func, '__qualname__', None)
                    if same_module and same_name:
                        logger.debug(
                            f"[ToolRegistry] Tool '{name}' already registered by same impl "
                            f"{func.__module__}.{func.__qualname__} — skipping re-registration"
                        )
                    else:
                        logger.debug(
                            f"[ToolRegistry] Tool '{name}' is being re-registered by "
                            f"{func.__module__}.{func.__qualname__} (was {existing_name})"
                        )
            # Update schema in-place or append
            for idx, s in enumerate(TOOL_SCHEMAS):
                if s.get("name") == name:
                    TOOL_SCHEMAS[idx] = schema
                    break
            else:
                TOOL_SCHEMAS.append(schema)
            TOOL_REGISTRY[name] = func

        # Register in the canonical ToolRuntime
        try:
            from .runtime import get_canonical_tool_runtime
            from .domain import ToolCategory, RiskLevel, VerificationStrategy
            cat_enum = ToolCategory.GENERAL
            try:
                cat_enum = ToolCategory(category.lower())
            except Exception:
                pass
            risk_enum = RiskLevel.LOW
            try:
                risk_enum = RiskLevel(risk_level.lower())
            except Exception:
                pass
            ver_enum = VerificationStrategy.NONE
            try:
                ver_enum = VerificationStrategy(verification_strategy.upper())
            except Exception:
                pass

            get_canonical_tool_runtime().register_tool(
                name=name,
                description=description,
                handler=func,
                parameters=parameters or {},
                category=cat_enum,
                risk_level=risk_enum,
                permission_required=permission_required,
                approval_required=approval_required,
                is_read_only=is_read_only,
                idempotent=idempotent,
                timeout_sec=timeout_sec,
                verification_strategy=ver_enum,
            )
        except Exception as exc:
            logger.debug("[ToolRegistry] Canonical ToolRuntime registration note: %s", exc)

        return func
    return decorator


_WORKER_POOL: Any = None


def _get_worker_pool():
    global _WORKER_POOL
    if _WORKER_POOL is None:
        import concurrent.futures
        _WORKER_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="jarvis_tool_worker")
    return _WORKER_POOL


def _run_async(coro):
    """
    Helper to run asynchronous coroutines safely, even inside a running loop.
    Avoids event loop deadlocks by executing on a dedicated background thread
    with its own event loop when the current thread's event loop is active.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Running loop is active on this thread. To prevent blocking/deadlocking it,
        # run the coroutine in a separate background thread with its own loop.
        import threading
        result_holder = []
        exception_holder = []

        def worker():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                res = new_loop.run_until_complete(coro)
                result_holder.append(res)
            except Exception as e:
                exception_holder.append(e)
            finally:
                # ISSUE-3 FIX: Always close the loop — prevents resource leak even on timeout/exception
                try:
                    new_loop.close()
                except Exception:
                    pass

        # ISSUE-3 FIX: daemon=True so abandoned (timed-out) threads are reaped by Python GC
        # on process exit instead of accumulating as zombies consuming memory + sockets
        thread = threading.Thread(target=worker, name="jarvis_async_bridge", daemon=True)
        thread.start()
        thread.join(timeout=60.0)

        if thread.is_alive():
            # Thread exceeded timeout — it will be cleaned up when process exits (daemon)
            raise TimeoutError("Async tool call timed out after 60 seconds — operation abandoned")

        if exception_holder:
            raise exception_holder[0]

        return result_holder[0] if result_holder else None
    else:
        return asyncio.run(coro)




def get_tool_prompt_block() -> str:
    """Generate the system prompt block defining all available tools and skill templates."""
    _import_plugins(full=True)

    schema_text = json.dumps(TOOL_SCHEMAS, indent=2)

    # Load available skills catalog dynamically to avoid circular import cycles
    skills_block = ""
    try:
        try:
            from brjarvis.skills import load_skills
        except ImportError:
            from skills import load_skills
        skills = [s for s in load_skills() if getattr(s, "user_invocable", True)]
        if skills:
            skills_lines = [
                "\n### Available Skill Templates",
                "You can execute any of these templates using the `run_skill` tool:",
            ]
            for s in skills:
                triggers_str = ", ".join(s.triggers)
                skills_lines.append(f"- **{s.name}** (triggers: {triggers_str}): {s.description}")
            skills_block = "\n".join(skills_lines) + "\n"
    except Exception:
        pass

    return f"""
## Available Tools

To use a tool, output EXACTLY this JSON block on its own line:

```tool_call
{{"tool": "<tool_name>", "args": {{<arguments>}}}}
```

After you output a tool_call block, execution pauses while the tool runs.
You will then receive the tool result and can continue.

If you do NOT need a tool, just respond normally with text.
NEVER fabricate tool results. Always call the tool if you need real data.

**POLICY MODE**: Tool execution is enforced by the active permissions policy.
{skills_block}
### Tool Definitions
{schema_text}
"""


def get_pruned_tool_prompt_block(user_prompt: str = "") -> str:
    """
    Generate a lightweight, intent-pruned tool system prompt block.
    Filters available tool definitions down to the most relevant tools, saving up to 80% prompt tokens.
    """
    # ── Lazy Loading of Plugins based on query context ──
    _import_plugins(full=False)  # always import core plugins

    low = (user_prompt or "").lower()
    if low:
        # Map keyword patterns to their specific extended plugin modules
        keyword_to_plugins = {
            ("whatsapp", "watsapp", "wp"): ["tools.whatsapp_tools"],
            ("calendar", "event", "schedule"): ["tools.calendar_tools"],
            ("email", "gmail", "mail"): ["tools.gmail_auth_tools", "tools.smart_email_tools"],
            ("excel", "xlsx", "sheet", "spreadsheet"): ["tools.excel_tools"],
            ("git", "repo", "github", "codebase", "repository"): ["tools.git_repo_tool"],
            ("doc", "document", "docx", "word", "pdf", "report", "walkthrough", "paper", "presentation", "manual"): ["tools.doc_tools", "tools.pdf_tools"],
            ("diagnostic", "diagnostic_tool", "health", "system_health"): ["tools.system_diagnostic_tool", "tools.system_health"],
            ("screen", "see", "look", "click", "capture"): ["tools.image_tools"],
            ("flight", "ticket", "airline", "fly"): ["tools.legacy_actions_tools"],
            ("contact", "contacts", "vcf", "phone", "addressbook"): ["tools.contact_tools"],
            ("connector", "hub", "notion", "slack", "rss", "wikipedia"): ["tools.connector_tools"],
            ("reminder", "alarm", "schedule_reminder"): ["tools.reminder_tools"],
            ("scratchpad", "scratch", "snippet", "eval"): ["tools.scratchpad_tools"],
            ("background_monitor", "monitor_topic", "topic_monitor", "news_monitor"): ["tools.background_monitor_tools"],
            ("import_file", "ingest", "file_processor"): ["tools.file_import_tools", "tools.file_processor_tools"],
            ("remember_that", "recall"): ["tools.recall_tools"],
            ("career", "job", "jobs", "resume", "interview", "offer", "application", "ats", "recruiter", "hiring", "cv"): ["career.tools"],
        }
        for keywords, plugins in keyword_to_plugins.items():
            if any(kw in low for kw in keywords):
                for p in plugins:
                    _import_plugins(plugin_name=p)

    if not user_prompt:
        return get_tool_prompt_block()

    low = user_prompt.lower()

    
    # Core high-frequency tools always available
    essential_tools = {
        "open_app", "web_search", "file_read", "file_write", "run_code", "computer_settings", "window_manager",
        "computer_control", "list_installed_applications", "list_running_applications", "send_whatsapp",
        "create_calendar_event", "list_calendar_events", "send_email", "gmail_login", "automate_app",
        "run_automation_workflow", "create_word_document", "create_pdf_document", "document_creator"
    }
    
    # Domain keyword matching for targeted tool inclusion
    domain_map = {
        ("search", "google", "find", "who is", "what is", "news", "price", "weather"): {"web_search", "fetch_page"},
        ("file", "read", "write", "save", "folder", "directory", "txt", "csv", "json"): {"file_read", "file_write", "file_list", "file_delete", "file_search"},
        ("doc", "docx", "word", "document", "report", "pdf", "walkthrough", "paper", "compare", "comparison", "recommendation", "letter", "greeting"): {"create_word_document", "create_pdf_document", "document_creator", "generate_walkthrough", "file_read", "file_write"},
        ("git", "repo", "github", "repository", "codebase", "branch", "commit"): {"git_repo_mgr", "file_read", "file_write", "file_list"},
        ("app", "open", "launch", "close", "brave", "chrome", "edge", "notepad", "calculator", "window", "process", "installed", "running"): {"open_app", "computer_settings", "window_manager", "list_installed_applications", "list_running_applications", "search_applications", "get_app_launch_history", "get_app_usage_statistics", "automate_app"},
        ("whatsapp", "watsapp", "whats app", "wats app", "wapp", "wp", "chat", "message", "contact", "text", "send", "say", "tell", "hii", "hiii", "hello"): {"send_whatsapp", "schedule_whatsapp_message", "manage_whatsapp_contacts"},
        ("calendar", "event", "schedule", "task", "meeting", "reminder"): {"create_calendar_event", "list_calendar_events", "search_calendar_events", "delete_calendar_event"},
        ("email", "gmail", "g-mail", "mail", "inbox", "compose", "letter", "greeting", "greetings", "smtp", "login", "send", "say", "tell", "draft"): {"send_email", "schedule_email", "manage_email_contacts", "gmail_login", "get_gmail_auth_status", "gmail_logout", "open_app", "automate_app", "computer_control"},
        ("screen", "see", "look", "click", "clik", "button", "tap", "press", "type", "mouse", "keyboard", "vision", "ocr", "capture", "display"): {"screen_find", "screen_click", "smart_click", "computer_control", "automate_app", "window_manager"},
        ("code", "python", "script", "execute", "eval", "debug", "run"): {"run_code", "scratchpad_write", "scratchpad_eval"},
        ("system", "volume", "brightness", "wifi", "battery", "restart", "shutdown", "diagnostic", "health", "cpu", "ram", "audit"): {"computer_settings", "system_diagnostic", "system_health"},
        ("youtube", "video", "play"): {"youtube_video"},
        ("flight", "ticket", "airline", "fly"): {"flight_finder"},
        ("game", "steam", "epic"): {"game_updater"},
        ("agent", "task", "subagent", "multi"): {"agent_task"},
        ("memory", "remember", "forget", "recall", "preference", "fact", "note"): {"memory_save", "memory_get", "memory_search", "memory_delete", "memory_forget", "memory_list", "memory_stats", "memory_reindex", "remember_that"},
        ("contact", "contacts", "vcf", "phone", "addressbook", "call"): {"import_contacts", "manage_contacts", "resolve_contact"},
        ("connector", "connectors", "hub", "notion", "slack", "rss", "wikipedia"): {"connector_status", "connector_call", "connector_search", "connector_add_mcp", "connector_list_tools"},
        ("reminder", "alarm", "schedule_reminder"): {"schedule_reminder", "manage_reminders", "reminder"},
        ("scratchpad", "scratch", "snippet"): {"scratchpad_write", "scratchpad_read", "scratchpad_eval", "scratchpad_list", "scratchpad_clear"},
        ("monitor", "background_monitor", "topic"): {"add_background_monitor", "remove_background_monitor", "list_monitored_topics", "check_monitored_topics"},
        ("import_file", "ingest", "file_processor", "ocr", "convert"): {"import_file_to_knowledge", "process_universal_file"},
        ("career", "job", "jobs", "resume", "interview", "offer", "application", "ats", "recruiter", "hiring", "cv", "tailor", "apply"): {
            "career_email_process", "career_offer_confirm", "career_spreadsheet_sync",
            "career_followup_generate_draft", "career_learning_insights", "career_profile_get",
            "career_profile_update", "career_job_search", "career_job_match", "career_resume_build",
            "career_resume_tailor", "career_resume_export", "career_ats_evaluate",
            "career_cover_letter_generate", "career_application_prepare", "career_application_submit",
            "career_application_verify", "career_application_track", "career_interview_prep",
            "career_analytics_report"
        },
    }

    selected_names = set(essential_tools)
    for keywords, tools in domain_map.items():
        if any(kw in low for kw in keywords):
            selected_names.update(tools)

    pruned_schemas = [schema for schema in TOOL_SCHEMAS if schema.get("name") in selected_names]
    
    # If pruning is too aggressive, fallback to full schemas
    if len(pruned_schemas) < 3:
        pruned_schemas = TOOL_SCHEMAS

    schema_text = json.dumps(pruned_schemas, indent=2)

    return f"""
## Available Tools (Intent-Pruned Context)

To use a tool, output EXACTLY this JSON block on its own line:

```tool_call
{{"tool": "<tool_name>", "args": {{<arguments>}}}}
```

After you output a tool_call block, execution pauses while the tool runs.
You will then receive the tool result and can continue.

**POLICY MODE**: Selected tools are still enforced by the active permissions policy.

### Tool Definitions
{schema_text}
"""


def execute_tool(
    name: str,
    args: dict | None = None,
    task_id: str = "",
    step_id: str = "",
    confirmed: bool = False,
) -> str:
    """
    Execute a tool through the canonical ToolRuntime and return a structured agent string.
    Never returns unverified raw success placeholders.
    """
    # Ensure core plugins are loaded
    _import_plugins(full=False)

    args_dict = dict(args) if isinstance(args, dict) else {}

    # Check lazy loading map if tool not loaded yet
    tool_to_module = {
        "send_whatsapp": "tools.whatsapp_tools",
        "schedule_whatsapp_message": "tools.whatsapp_tools",
        "manage_whatsapp_contacts": "tools.whatsapp_tools",
        "create_calendar_event": "tools.calendar_tools",
        "list_calendar_events": "tools.calendar_tools",
        "search_calendar_events": "tools.calendar_tools",
        "delete_calendar_event": "tools.calendar_tools",
        "send_email": "tools.smart_email_tools",
        "gmail_login": "tools.gmail_auth_tools",
        "gmail_logout": "tools.gmail_auth_tools",
        "get_gmail_auth_status": "tools.gmail_auth_tools",
        "create_word_document": "tools.doc_tools",
        "create_pdf_document": "tools.doc_tools",
        "document_creator": "tools.doc_tools",
        "generate_walkthrough": "tools.doc_tools",
        "pdf_extract_text": "tools.pdf_tools",
        "excel_analyze": "tools.excel_tools",
        "screen_find": "tools.image_tools",
        "screen_click": "tools.image_tools",
        "smart_click": "tools.image_tools",
        "git_repo_tool": "tools.git_repo_tool",
        "git_repo_mgr": "tools.git_repo_tool",
        "system_diagnostic": "tools.system_diagnostic_tool",
        "tool_health": "tools.system_diagnostic_tool",
        "mcp_connector": "tools.mcp_connector",
        "mcp_call_tool": "tools.mcp_connector",
        "file_read": "tools.file_tools",
        "file_write": "tools.file_tools",
        "file_list": "tools.file_tools",
        "file_delete": "tools.file_tools",
        "file_search": "tools.file_tools",
        "career_profile_get": "career.tools",
        "career_job_search": "career.tools",
        "career_resume_build": "career.tools",
    }

    if name in tool_to_module and name not in TOOL_REGISTRY:
        _import_plugins(plugin_name=tool_to_module[name])

    from .runtime import get_canonical_tool_runtime
    runtime = get_canonical_tool_runtime()

    # If not registered in ToolRuntime yet but in legacy TOOL_REGISTRY, bridge it
    if not runtime.get_tool_definition(name) and name in TOOL_REGISTRY:
        schema = next((s for s in TOOL_SCHEMAS if s.get("name") == name), {})
        runtime.register_tool(
            name=name,
            description=schema.get("description", ""),
            handler=TOOL_REGISTRY[name],
            parameters=schema.get("parameters"),
        )

    res = runtime.execute_tool(
        name=name,
        args=args_dict,
        task_id=task_id,
        step_id=step_id,
        confirmed=confirmed,
    )
    return res.to_agent_str()


def execute_tool_raw(
    name: str,
    args: dict | None = None,
    task_id: str = "",
    step_id: str = "",
    confirmed: bool = False,
) -> Any:
    """Execute tool and return the canonical ToolResult object directly."""
    _import_plugins(full=False)
    args_dict = dict(args) if isinstance(args, dict) else {}
    from .runtime import get_canonical_tool_runtime
    return get_canonical_tool_runtime().execute_tool(
        name=name,
        args=args_dict,
        task_id=task_id,
        step_id=step_id,
        confirmed=confirmed,
    )



def inspect_is_coroutine(obj) -> bool:
    """Check if object is a coroutine or future."""
    import inspect
    return inspect.iscoroutine(obj) or asyncio.iscoroutine(obj)


def set_orchestrator_ref(orchestrator: Any):
    """Set global reference to active orchestrator."""
    global _orchestrator_ref
    _orchestrator_ref = orchestrator


def get_orchestrator_ref() -> Any:
    """Get active orchestrator reference."""
    return _orchestrator_ref


def _lazy_register_tool(name: str, description: str, module_path: str, func_name: str, parameters: dict | None = None):
    def _lazy_wrapper(args: dict = None, **kwargs) -> Any:
        try:
            mod = importlib.import_module(module_path)
            target_func = getattr(mod, func_name)
            if args is not None and isinstance(args, dict):
                return target_func(args)
            elif kwargs:
                return target_func(**kwargs)
            return target_func(args or {})
        except Exception as exc:
            return f"ERROR: Failed to load tool handler '{name}' from {module_path}: {exc}"
    register_tool(name=name, description=description, parameters=parameters)(_lazy_wrapper)


_lazy_register_tool(
    name="reminder",
    description="Set or list smart reminders and desktop toast notifications. Args: 'action' ('add' or 'list'), 'text' (reminder message), 'time_str' (e.g. '9:00 AM', '14:30', 'tomorrow 9am'), 'delay_seconds' (optional integer).",
    module_path="actions.reminders",
    func_name="reminder_tool_action",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list"]},
            "text": {"type": "string", "description": "Reminder text"},
            "time_str": {"type": "string", "description": "Target time (e.g. '9am', '14:30')"},
            "delay_seconds": {"type": "integer", "description": "Delay in seconds"},
        },
        "required": ["action"],
    }
)

_lazy_register_tool(
    name="fast_file_search",
    description="High-speed desktop file search by filename or text content. Args: 'action' ('name' or 'content'), 'query' (search keyword), 'search_path' (optional directory path), 'extension' (optional file extension).",
    module_path="actions.fast_file_search",
    func_name="fast_file_search_action",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["name", "content"]},
            "query": {"type": "string", "description": "Search keyword or filename"},
            "search_path": {"type": "string", "description": "Root directory path"},
            "extension": {"type": "string", "description": "File extension filter"},
        },
        "required": ["action", "query"],
    }
)

_lazy_register_tool(
    name="longform_builder",
    description="Build comprehensive multi-volume books, technical manuals, research publications, and project toolkits automatically. Args: 'title' (book title), 'description' (topic focus), 'year' (publication year), 'folder_name' (optional output subfolder).",
    module_path="actions.longform_builder",
    func_name="longform_builder_action",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Title of the book or guide"},
            "description": {"type": "string", "description": "Detailed topic focus"},
            "year": {"type": "string", "description": "Target year (default: '2026')"},
            "folder_name": {"type": "string", "description": "Output folder name inside ./workspace/"},
        },
        "required": ["title", "description"],
    }
)




def parse_tool_call(text: str) -> tuple[str | None, dict | None]:
    """Parse a tool_call JSON block from LLM output."""

    # 0. XML/Token-based agent protocol parser (e.g. for gpt-oss-120b-medium)
    if "<|channel|>" in text or "<|message|>" in text:
        msg_match = _OSS_MESSAGE_RE.search(text)
        if msg_match:
            try:
                cleaned_json = re.sub(r'//.*', '', msg_match.group(1))
                data = json.loads(cleaned_json)
                
                tool_name = None
                args = {}
                
                if isinstance(data, dict):
                    if "name" in data:
                        tool_name = data.get("name")
                        args = data.get("args", {})
                    elif "tool" in data:
                        tool_name = data.get("tool")
                        args = data.get("args", {})
                
                if not tool_name:
                    preceding = text[:msg_match.start()]
                    tool_match = _OSS_TOOL_HINT_RE.search(preceding)
                    if tool_match:
                        matched_name = tool_match.group(1).split('.')[-1]
                        if matched_name != "tool_call":
                            tool_name = matched_name
                            args = data
                            
                if not tool_name and isinstance(data, dict):
                    if "code" in data:
                        tool_name = "run_code"
                        args = {"code": data.get("code"), "lang": data.get("lang", "python")}
                        
                if tool_name:
                    tool_name = str(tool_name).strip().split('.')[-1]
                    return tool_name, args
            except json.JSONDecodeError:
                pass

    # 1. Look for ```tool_call ... ``` format
    match = _TOOL_CALL_CODEBLOCK_RE.search(text)
    if match:
        try:
            # Clean comments or trailing commas if any
            cleaned_json = re.sub(r'//.*', '', match.group(1))
            data = json.loads(cleaned_json)
            if "tool" in data:
                return data.get("tool"), data.get("args", {})
            elif "code" in data:
                # Robust upgrade: automatically map direct code block tool calls to run_code tool
                return "run_code", {"code": data.get("code"), "lang": data.get("lang", "python")}
        except json.JSONDecodeError:
            pass

    # 2. Relaxed match for any {"tool": "...", "args": ...} block
    match2 = _TOOL_CALL_JSON_RE.search(text)
    if match2:
        try:
            data = json.loads(match2.group(1))
            return data.get("tool"), data.get("args", {})
        except json.JSONDecodeError:
            pass

    # 3. Relaxed match for direct code block
    match3 = _CODE_JSON_RE.search(text)
    if match3:
        try:
            data = json.loads(match3.group(1))
            return "run_code", {"code": data.get("code"), "lang": data.get("lang", "python")}
        except json.JSONDecodeError:
            pass

    return None, None


# Dynamic import list to populate TOOL_REGISTRY
_plugins_stage = 0  # 0=none, 1=core, 2=full
_plugins_lock = threading.Lock()
_loaded_plugins: set[str] = set()


def _import_plugins(*, full: bool = False, plugin_name: str | None = None):
    """Import tool plugin files to register their decorators.

    Refactored to support lazy-loading:
      - If plugin_name is provided, dynamically imports that specific plugin.
      - If full=False (default), imports only the 7 core essential tools immediately.
      - If full=True, imports all extended tools (e.g. for generating complete docs).
    """
    global _plugins_stage
    
    # Core essential tools needed immediately.
    # IMPORTANT: Any tool referenced in essential_tools or the system prompt MUST be
    # in this list — otherwise the LLM will be told a tool exists but get
    # 'ERROR: Unknown tool' when it tries to call it.
    core_plugins = [
        "tools.web_tools",
        "tools.file_tools",
        "tools.code_tools",
        "tools.pc_tools",
        "tools.memory_tools",
        "tools.agent_tools",
        "tools.system_tools",
        # FIX: these plugins define tools listed in essential_tools / the system
        # prompt, so they must load at startup — not lazily on first use.
        "tools.legacy_actions_tools",   # open_app, computer_settings, agent_task,
                                         # code_helper, dev_agent, youtube_video,
                                         # flight_finder, file_controller, screen_process
        "tools.automation_tools",        # automate_app, run_automation_workflow,
                                         # execute_system_automation
        "tools.app_analyzer_tools",      # list_installed_applications,
                                         # list_running_applications
        "tools.app_tracker_tools",       # get_app_launch_history,
                                         # get_app_usage_statistics
        "tools.skills_tools",             # run_skill, list_skills
    ]

    # Extended plugins loaded on demand or after core.
    # NOTE: Plugins already in core_plugins are skipped via _loaded_plugins guard.
    extended_plugins = [
        "tools.redteam_tools",
        "tools.skills_tools",
        "actions.clipboard_history",
        "actions.scheduler",
        "actions.email_assistant",
        "tools.image_tools",
        "tools.video_tools",
        "tools.rag_tools",
        "tools.transcription_tools",
        "tools.custom_command_tools",
        "tools.export_tools",
        "tools.live_os_tools",
        "tools.excel_tools",
        "tools.process_tools",
        "tools.audit_tools",
        "tools.doc_tools",
        "tools.workspace_tools",
        "tools.app_connectors",
        "tools.code_refactor_tool",
        "tools.system_diagnostic_tool",
        "tools.batch_file_tool",
        "tools.git_repo_tool",
        # NOTE: browser_automation and connector_tools removed from here —
        # they are already loaded in core_plugins, preventing double-registration.
        "tools.qa_testing_tool",
        "tools.autonomous_browser_agent",
        "tools.whatsapp_tools",
        "tools.telegram_tools",
        "tools.calendar_tools",
        "tools.gmail_auth_tools",
        "tools.smart_email_tools",
        "tools.file_search_semantic",
        "tools.web_extractor",
        "tools.system_health",
        "tools.mcp_connector",
        "tools.web_app_tools",
        "tools.pdf_tools",
        "tools.proactive_listener_tools",
        "tools.browser_agent_v2",
        "tools.background_monitor_tools",
        # NOTE: connector_tools removed — already in core_plugins.
        "tools.contact_tools",
        "tools.file_import_tools",
        "tools.file_processor_tools",
        "tools.recall_tools",
        "tools.reminder_tools",
        "tools.scratchpad_tools",
    ]



    def _import_single(mod_name: str) -> None:
        try:
            importlib.import_module(mod_name)
            _REGISTRATION_ERRORS.pop(mod_name, None)
        except (ImportError, ModuleNotFoundError):
            if not mod_name.startswith("brjarvis."):
                alt = f"brjarvis.{mod_name}"
                importlib.import_module(alt)
                _REGISTRATION_ERRORS.pop(mod_name, None)
            else:
                raise

    with _plugins_lock:
        # 1. Handle single-plugin lazy request
        if plugin_name:
            if plugin_name in _loaded_plugins:
                return
            try:
                _import_single(plugin_name)
                _loaded_plugins.add(plugin_name)
                logger.debug("[ToolRegistry] Lazy loaded extended plugin: %s", plugin_name)
            except Exception as exc:
                _REGISTRATION_ERRORS[plugin_name] = str(exc)
                logger.warning("[ToolRegistry] Failed to lazy load plugin '%s': %s", plugin_name, exc)
            return

        target_stage = 2 if full else 1
        if _plugins_stage >= target_stage:
            return

        if _plugins_stage < 1:
            for p in core_plugins:
                try:
                    _import_single(p)
                    _loaded_plugins.add(p)
                except Exception as exc:
                    _REGISTRATION_ERRORS[p] = str(exc)
                    logger.debug("[ToolRegistry] Core plugin '%s' import notice: %s", p, exc)
            _plugins_stage = 1

        if full and _plugins_stage < 2:
            for p in extended_plugins:
                if p not in _loaded_plugins:
                    try:
                        _import_single(p)
                        _loaded_plugins.add(p)
                    except Exception as exc:
                        _REGISTRATION_ERRORS[p] = str(exc)
                        logger.debug("[ToolRegistry] Extended plugin '%s' import notice: %s", p, exc)

            # NOTE: career.tools are loaded implicitly when brjarvis.career is first
            # imported (via career/__init__.py -> from . import tools). Calling
            # _import_single('career.tools') here would cause double-registration.
            # We mark it as loaded so the guard prevents future redundant loads.
            _loaded_plugins.add("career.tools")
            _loaded_plugins.add("brjarvis.career.tools")

            # Load custom plugins
            try:
                from plugins import load_custom_plugins
                load_custom_plugins()
            except Exception as exc:
                logger.debug("[ToolRegistry] Custom plugins load notice: %s", exc)

            _plugins_stage = 2


def get_registry_status() -> dict[str, Any]:
    """Return a comprehensive health audit of the Tool Registry ecosystem."""
    _import_plugins(full=True)
    return {
        "discovered": len(TOOL_SCHEMAS),
        "registered": len(TOOL_REGISTRY),
        "healthy": len(TOOL_REGISTRY),
        "disabled": 0,
        "failed": dict(_REGISTRATION_ERRORS),
        "tool_names": sorted(list(TOOL_REGISTRY.keys())),
    }


