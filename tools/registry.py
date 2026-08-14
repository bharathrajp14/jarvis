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

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Global registry mappings
TOOL_SCHEMAS: list[dict] = []
TOOL_REGISTRY: dict[str, Callable[[dict], Any]] = {}

# Thread-safe lock protecting TOOL_SCHEMAS and TOOL_REGISTRY mutations
_REGISTRY_LOCK = threading.RLock()

# Cache references
_orchestrator_ref: Any = None


_TOOL_CALL_CODEBLOCK_RE = re.compile(r'```tool_call\s*\n\s*(\{.*?\})\s*\n\s*```', re.DOTALL)
_TOOL_CALL_JSON_RE = re.compile(r'(\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{.*?\}\s*\})', re.DOTALL)
_CODE_JSON_RE = re.compile(r'(\{\s*"code"\s*:\s*"[^"]+"\s*,\s*"lang"\s*:\s*"[^"]+"\s*\})', re.DOTALL)
_OSS_MESSAGE_RE = re.compile(r'<\|message\|>\s*(\{.*?\})', re.DOTALL)
_OSS_TOOL_HINT_RE = re.compile(r'(?:to|call)=?([\w\.\-]+)')


def register_tool(name: str, description: str, parameters: dict | None = None) -> Callable:
    """Decorator to register a tool function in the JARVIS registry (thread-safe).

    Logs a WARNING if an existing tool is overwritten, so silent clobbering is
    visible during debugging.
    """
    def decorator(func: Callable[[dict], Any]) -> Callable[[dict], Any]:
        schema = {
            "name": name,
            "description": description,
            "parameters": parameters or {}
        }
        with _REGISTRY_LOCK:
            # Warn if overwriting an existing tool registration
            if name in TOOL_REGISTRY and TOOL_REGISTRY[name] is not func:
                logger.warning(
                    f"[ToolRegistry] Tool '{name}' is being re-registered by "
                    f"{func.__module__}.{func.__qualname__} (was {TOOL_REGISTRY[name].__qualname__})"
                )
            # Avoid duplicate schemas
            if not any(s["name"] == name for s in TOOL_SCHEMAS):
                TOOL_SCHEMAS.append(schema)
            TOOL_REGISTRY[name] = func

        # Also register in the unified ToolRuntimeEngine
        try:
            from tools.tool_runtime import get_tool_runtime
            get_tool_runtime().register_tool(
                name=name,
                description=description,
                handler=func,
                parameters=parameters
            )
        except Exception as exc:
            logger.debug("[ToolRegistry] ToolRuntimeEngine registration fallback: %s", exc)

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
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                res = new_loop.run_until_complete(coro)
                result_holder.append(res)
                new_loop.close()
            except Exception as e:
                exception_holder.append(e)

        thread = threading.Thread(target=worker, name="jarvis_async_bridge")
        thread.start()
        thread.join(timeout=60.0)

        if thread.is_alive():
            raise TimeoutError("Async tool call timed out after 60 seconds")

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
            ("excel", "xlsx"): ["tools.excel_tools"],
            ("git", "repo", "github"): ["tools.git_repo_tool"],
            ("diagnostic", "diagnostic_tool"): ["tools.system_diagnostic_tool"],
            ("screen", "see", "look", "click", "capture"): ["tools.image_tools"],
            ("flight", "ticket", "airline", "fly"): ["tools.legacy_actions_tools"],
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
        "list_installed_applications", "list_running_applications", "send_whatsapp", "create_calendar_event",
        "list_calendar_events", "send_email", "gmail_login", "automate_app", "run_automation_workflow"
    }
    
    # Domain keyword matching for targeted tool inclusion
    domain_map = {
        ("search", "google", "find", "who is", "what is", "news", "price", "weather"): {"web_search", "fetch_page"},
        ("file", "read", "write", "save", "folder", "directory", "document", "txt", "csv", "json", "pdf", "docx"): {"file_read", "file_write", "file_list", "file_delete", "file_search"},
        ("app", "open", "launch", "close", "brave", "chrome", "edge", "notepad", "calculator", "window", "process", "installed", "running"): {"open_app", "computer_settings", "window_manager", "list_installed_applications", "list_running_applications", "search_applications", "get_app_launch_history", "get_app_usage_statistics"},
        ("whatsapp", "watsapp", "whats app", "wats app", "wapp", "wp", "chat", "message", "contact", "text", "send", "say", "tell", "hii", "hiii", "hello"): {"send_whatsapp", "schedule_whatsapp_message", "manage_whatsapp_contacts"},
        ("calendar", "event", "schedule", "task", "meeting", "reminder"): {"create_calendar_event", "list_calendar_events", "search_calendar_events", "delete_calendar_event"},
        ("email", "gmail", "g-mail", "mail", "inbox", "smtp", "login", "send", "say", "tell", "draft"): {"send_email", "schedule_email", "manage_email_contacts", "gmail_login", "get_gmail_auth_status", "gmail_logout"},
        ("automate", "workflow", "macro", "script", "system"): {"automate_app", "run_automation_workflow", "execute_system_automation"},
        ("screen", "see", "look", "click", "vision", "ocr", "capture", "display"): {"screen_find", "screen_click", "smart_click"},
        ("code", "python", "script", "execute", "eval", "debug", "run"): {"run_code", "scratchpad_write", "scratchpad_eval"},
        ("system", "volume", "brightness", "wifi", "battery", "restart", "shutdown", "diagnostic", "cpu", "ram"): {"computer_settings", "system_diagnostic"},
        ("youtube", "video", "play"): {"youtube_video"},
        ("flight", "ticket", "airline", "fly"): {"flight_finder"},
        ("game", "steam", "epic"): {"game_updater"},
        ("agent", "task", "subagent", "multi"): {"agent_task"},
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


def execute_tool(name: str, args: dict) -> str:
    """Execute a registered tool by name. All errors are caught and returned as strings."""
    # Ensure core plugins are loaded
    _import_plugins(full=False)


    # Map aliases for ReAct loop execution
    if name in ("browser_control", "open_browser", "web_browser"):
        name = "open_app"
        url = args.get("url") or args.get("query") or args.get("app_name") or ""
        args = {"app_name": f"chrome {url}".strip() if url else "chrome"}
    elif name in ("system_control", "desktop_type"):
        name = "computer_settings"
        text = args.get("text") or args.get("value") or args.get("description") or ""
        act = args.get("action", "type_text")
        if act in ("type", "write", "type_text", "write_text"):
            act = "type_text"
        args = {"action": act, "value": text}
    elif name in ("file_controller", "file_manager", "file_control"):
        act = str(args.get("action", "read")).lower()
        if act in ("create", "write", "create_file", "save"):
            name = "file_write"
            args = {"path": args.get("name") or args.get("path") or "file.txt", "content": args.get("content", "")}
        elif act in ("read", "get", "view", "cat", "open_read"):
            name = "file_read"
            args = {"path": args.get("path") or args.get("name") or "file.txt"}
        elif act in ("list", "dir", "ls", "search"):
            name = "file_list"
            args = {"path": args.get("path", ".")}
        elif act in ("open", "launch", "open_file", "view_doc"):
            name = "open_app"
            target_path = args.get("path") or args.get("name") or args.get("file") or ""
            args = {"app_name": f"start {target_path}".strip() if target_path else "explorer"}
        else:
            name = "file_list"
            args = {"path": args.get("path", ".")}
    elif name in ("screen_process", "screen_processor", "screen_share", "screen_shot"):
        name = "screen_find"
        desc = args.get("description") or args.get("query") or args.get("text") or "screen"
        args = {"description": str(desc)}
    elif name == "window_control":  # keep only the non-registered alias
        name = "window_manager"
        args = {"action": args.get("action", "list"), "title": args.get("title", "")}


    # ── Lazy Loading Resolve ──
    if name not in TOOL_REGISTRY:
        tool_to_module = {
            # WhatsApp
            "send_whatsapp": "tools.whatsapp_tools",
            "schedule_whatsapp_message": "tools.whatsapp_tools",
            "manage_whatsapp_contacts": "tools.whatsapp_tools",
            # Calendar
            "create_calendar_event": "tools.calendar_tools",
            "list_calendar_events": "tools.calendar_tools",
            "search_calendar_events": "tools.calendar_tools",
            "delete_calendar_event": "tools.calendar_tools",
            # Email / Gmail
            "send_email": "tools.smart_email_tools",
            "gmail_login": "tools.gmail_auth_tools",
            "gmail_logout": "tools.gmail_auth_tools",
            "get_gmail_auth_status": "tools.gmail_auth_tools",
            # Document / Excel
            "excel_analyze": "tools.excel_tools",
            "flight_finder": "tools.legacy_actions_tools",
            "screen_find": "tools.image_tools",
            "screen_click": "tools.image_tools",
            "smart_click": "tools.image_tools",
            "git_repo_tool": "tools.git_repo_tool",
            "system_diagnostic": "tools.system_diagnostic_tool",
            "mcp_connector": "tools.mcp_connector",
            "mcp_call_tool": "tools.mcp_connector",
            "start_multichannel_listener": "tools.proactive_listener_tools",
            "stop_multichannel_listener": "tools.proactive_listener_tools",
            "get_pending_channel_actions": "tools.proactive_listener_tools",
            "respond_channel_action": "tools.proactive_listener_tools",
        }

        if name in tool_to_module:
            _import_plugins(plugin_name=tool_to_module[name])

    if name not in TOOL_REGISTRY:
        return f"ERROR: Unknown tool '{name}'"


    # ── Permission enforcement (Fail-Closed) ──────────────────────────────
    try:
        from permissions import check_permission
        if not check_permission(name, args):
            return f"PERMISSION DENIED: Tool '{name}' is blocked by current security policy. Change JARVIS_PERMISSION_MODE in .env to allow_all to override."
    except Exception as perm_err:
        logger.error("Permission check failed closed for tool '%s': %s", name, perm_err)
        return f"PERMISSION DENIED: Tool '{name}' verification failed (Fail-Closed Policy Engine)."


    try:
        func = TOOL_REGISTRY[name]
        if not isinstance(args, dict):
            args = {}
        
        import inspect
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        if len(params) == 1 and params[0] in ("args", "kwargs", "data", "payload", "input_data"):
            result = func(args)
        else:
            try:
                result = func(**args)
            except TypeError:
                result = func(args)

        if inspect_is_coroutine(result):
            result = _run_async(result)
        return str(result)
    except PermissionError as e:
        return f"SCOPE VIOLATION: {e}"
    except Exception as e:
        tb = traceback.format_exc()
        return f"TOOL ERROR ({name}): {e}\n{tb}"


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


try:
    from actions.reminders import reminder_tool_action
    register_tool(
        name="reminder",
        description="Set or list smart reminders and desktop toast notifications. Args: 'action' ('add' or 'list'), 'text' (reminder message), 'time_str' (e.g. '9:00 AM', '14:30', 'tomorrow 9am'), 'delay_seconds' (optional integer).",
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
    )(reminder_tool_action)
except Exception as exc:
    logger.debug(f"[Tools] Failed to register reminder tool: {exc}")

try:
    from actions.fast_file_search import fast_file_search_action
    register_tool(
        name="fast_file_search",
        description="High-speed desktop file search by filename or text content. Args: 'action' ('name' or 'content'), 'query' (search keyword), 'search_path' (optional directory path), 'extension' (optional file extension).",
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
    )(fast_file_search_action)
except Exception as exc:
    logger.debug(f"[Tools] Failed to register fast_file_search tool: {exc}")

try:
    from actions.longform_builder import longform_builder_action
    register_tool(
        name="longform_builder",
        description="Build comprehensive multi-volume books, technical manuals, research publications, and project toolkits automatically. Args: 'title' (book title), 'description' (topic focus), 'year' (publication year), 'folder_name' (optional output subfolder).",
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
    )(longform_builder_action)
except Exception as exc:
    logger.debug(f"[Tools] Failed to register longform_builder tool: {exc}")

try:
    from actions.system_optimizer import system_optimizer_action
    register_tool(
        name="system_optimizer",
        description="Run automated RAM, garbage collection, and temporary file cache optimization. Returns memory stats.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["optimize"]}
            }
        }
    )(system_optimizer_action)
except Exception as exc:
    logger.debug(f"[Tools] Failed to register system_optimizer tool: {exc}")

try:
    from tools.window_manager import window_manager_action
    register_tool(
        name="window_manager",
        description="Inspect visible desktop window titles and focus/switch applications. Args: 'action' ('list' or 'focus'), 'title' (optional application window title).",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "focus"]},
                "title": {"type": "string", "description": "Title or partial title of window to focus"}
            },
            "required": ["action"]
        }
    )(window_manager_action)
except Exception as exc:
    logger.debug(f"[Tools] Failed to register window_manager tool: {exc}")

try:
    from tools.web_extractor import web_extractor_action
    register_tool(
        name="web_extractor",
        description="Extract clean text content, headers, and main article text from any web URL. Args: 'url' (webpage URL).",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target webpage URL to fetch and extract"}
            },
            "required": ["url"]
        }
    )(web_extractor_action)
except Exception:
    pass

try:
    from tools.system_health import system_health_action
    register_tool(
        name="system_health",
        description="Retrieve system health metrics including CPU load, RAM usage, storage, and battery state.",
        parameters={
            "type": "object",
            "properties": {}
        }
    )(system_health_action)
except Exception:
    pass

try:
    from tools.file_search_semantic import file_search_semantic_action
    register_tool(
        name="file_search_semantic",
        description="Fast natural language semantic file search across workspace files. Args: 'query' (search term or file description).",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language file description or keywords"}
            },
            "required": ["query"]
        }
    )(file_search_semantic_action)
except Exception:
    pass


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
        "tools.browser_automation",
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
    ]



    with _plugins_lock:
        # 1. Handle single-plugin lazy request
        if plugin_name:
            if plugin_name in _loaded_plugins:
                return
            try:
                importlib.import_module(plugin_name)
                _loaded_plugins.add(plugin_name)
                logger.debug("[ToolRegistry] Lazy loaded extended plugin: %s", plugin_name)
            except Exception as exc:
                logger.warning("[ToolRegistry] Failed to lazy load plugin '%s': %s", plugin_name, exc)
            return

        target_stage = 2 if full else 1
        if _plugins_stage >= target_stage:
            return

        if _plugins_stage < 1:
            for p in core_plugins:
                try:
                    importlib.import_module(p)
                    _loaded_plugins.add(p)
                except Exception as exc:
                    logger.debug("[ToolRegistry] Core plugin '%s' import notice: %s", p, exc)
            _plugins_stage = 1

        if full and _plugins_stage < 2:
            for p in extended_plugins:
                if p not in _loaded_plugins:
                    try:
                        importlib.import_module(p)
                        _loaded_plugins.add(p)
                    except Exception as exc:
                        # Suppress non-critical optional tool import failures
                        logger.debug("[ToolRegistry] Extended plugin '%s' import notice: %s", p, exc)

            # Load custom plugins
            try:
                from plugins import load_custom_plugins
                load_custom_plugins()
            except Exception as exc:
                logger.debug("[ToolRegistry] Custom plugins load notice: %s", exc)

            _plugins_stage = 2


