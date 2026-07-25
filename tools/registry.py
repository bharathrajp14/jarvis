# tools/registry.py — JARVIS MK37 Universal Tool Registry
"""
Universal tool registry and executor for JARVIS MK37.
Uses a decorator-based plugin system to register and execute tools.
"""
from __future__ import annotations

import asyncio
import json
import traceback
import sys
import importlib
from pathlib import Path
from typing import Callable, Any

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Global registry mappings
TOOL_SCHEMAS: list[dict] = []
TOOL_REGISTRY: dict[str, Callable[[dict], Any]] = {}

# Cache references
_orchestrator_ref: Any = None


def register_tool(name: str, description: str, parameters: dict | None = None) -> Callable:
    """Decorator to register a tool function in the JARVIS registry."""
    def decorator(func: Callable[[dict], Any]) -> Callable[[dict], Any]:
        schema = {
            "name": name,
            "description": description,
            "parameters": parameters or {}
        }
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
        except Exception:
            pass

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
    Handles loop thread safety to prevent deadlocks or thread attachment errors.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        pool = _get_worker_pool()
        return pool.submit(lambda: asyncio.run(coro)).result(timeout=60)
    else:
        return asyncio.run(coro)


def get_tool_prompt_block() -> str:
    """Generate the system prompt block defining all available tools."""
    _import_plugins()
    schema_text = json.dumps(TOOL_SCHEMAS, indent=2)
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

**AUTO-ALLOW MODE**: All tools execute immediately without confirmation.

### Tool Definitions
{schema_text}
"""


def get_pruned_tool_prompt_block(user_prompt: str = "") -> str:
    """
    Generate a lightweight, intent-pruned tool system prompt block.
    Filters available tool definitions down to the most relevant tools, saving up to 80% prompt tokens.
    """
    _import_plugins()

    if not user_prompt:
        return get_tool_prompt_block()

    low = user_prompt.lower()
    
    # Core high-frequency tools always available
    essential_tools = {"open_app", "web_search", "file_read", "file_write", "run_code", "computer_settings"}
    
    # Domain keyword matching for targeted tool inclusion
    domain_map = {
        ("search", "google", "find", "who is", "what is", "news", "price", "weather"): {"web_search", "fetch_page"},
        ("file", "read", "write", "save", "folder", "directory", "document", "txt", "csv", "json", "pdf", "docx"): {"file_read", "file_write", "file_list", "file_delete", "file_search"},
        ("app", "open", "launch", "close", "brave", "chrome", "edge", "notepad", "calculator"): {"open_app", "computer_settings"},
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

**AUTO-ALLOW MODE**: Selected tools execute immediately without confirmation.

### Tool Definitions
{schema_text}
"""


def execute_tool(name: str, args: dict) -> str:
    """Execute a registered tool by name. All errors are caught and returned as strings."""
    # Ensure all plugins are imported/registered
    _import_plugins()

    # Map aliases for ReAct loop execution
    if name in ("browser_control", "open_browser", "web_browser"):
        name = "open_app"
        url = args.get("url") or args.get("query") or args.get("app_name") or ""
        args = {"app_name": f"chrome {url}".strip() if url else "chrome"}
    elif name in ("computer_control", "system_control", "desktop_type"):
        name = "computer_settings"
        text = args.get("text") or args.get("value") or args.get("description") or ""
        act = args.get("action", "type_text")
        if act in ("type", "write", "type_text", "write_text"):
            act = "type_text"
        args = {"action": act, "value": text}
    elif name in ("file_controller", "file_manager"):
        act = args.get("action", "write")
        if act in ("create", "write", "create_file"):
            name = "file_write"
            args = {"path": args.get("name") or args.get("path") or "file.txt", "content": args.get("content", "")}
        elif act in ("list", "dir", "ls"):
            name = "file_list"
            args = {"path": args.get("path", ".")}

    if name not in TOOL_REGISTRY:
        return f"ERROR: Unknown tool '{name}'"

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


def parse_tool_call(text: str) -> tuple[str | None, dict | None]:
    """Parse a tool_call JSON block from LLM output."""
    import re
    
    # 0. XML/Token-based agent protocol parser (e.g. for gpt-oss-120b-medium)
    if "<|channel|>" in text or "<|message|>" in text:
        msg_match = re.search(r'<\|message\|>\s*(\{.*?\})', text, re.DOTALL)
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
                    tool_match = re.search(r'(?:to|call)=?([\w\.\-]+)', preceding)
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
    pattern = r'```tool_call\s*\n\s*(\{.*?\})\s*\n\s*```'
    match = re.search(pattern, text, re.DOTALL)
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
    pattern2 = r'(\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{.*?\}\s*\})'
    match2 = re.search(pattern2, text, re.DOTALL)
    if match2:
        try:
            data = json.loads(match2.group(1))
            return data.get("tool"), data.get("args", {})
        except json.JSONDecodeError:
            pass

    # 3. Relaxed match for direct code block
    pattern3 = r'(\{\s*"code"\s*:\s*"[^"]+"\s*,\s*"lang"\s*:\s*"[^"]+"\s*\})'
    match3 = re.search(pattern3, text, re.DOTALL)
    if match3:
        try:
            data = json.loads(match3.group(1))
            return "run_code", {"code": data.get("code"), "lang": data.get("lang", "python")}
        except json.JSONDecodeError:
            pass

    return None, None


# Dynamic import list to populate TOOL_REGISTRY
_plugins_loaded = False

def _import_plugins():
    """Import all tool plugin files to register their decorators."""
    global _plugins_loaded
    if _plugins_loaded:
        return

    plugins = [
        "tools.web_tools",
        "tools.file_tools",
        "tools.code_tools",
        "tools.pc_tools",
        "tools.memory_tools",
        "tools.agent_tools",
        "tools.redteam_tools",
        "tools.system_tools",
        "tools.skills_tools",
        "tools.legacy_actions_tools",
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
    ]

    for p in plugins:
        try:
            importlib.import_module(p)
        except Exception as e:
            print(f"[JARVIS] Tool Plugin Error: Failed to load '{p}' — {e}")
            traceback.print_exc()

    # Load custom plugins
    try:
        from plugins import load_custom_plugins
        load_custom_plugins()
    except Exception as e:
        print(f"[JARVIS] Custom plugins loader warning: {e}")

    _plugins_loaded = True


def get_pruned_tool_prompt_block(user_prompt: str = "") -> str:
    """
    Antigravity Dynamic Tool Signature Pruning.
    Filters the tool registry so only tools relevant to the user prompt are included in system instructions.
    Reduces system prompt size by ~85%!
    Core general-purpose tools are ALWAYS preserved to prevent hallucinations.
    """
    _import_plugins()
    if not TOOL_SCHEMAS:
        return ""

    if not user_prompt:
        return get_tool_prompt_block()

    prompt_lower = user_prompt.lower()
    selected = []
    
    # Core general-purpose tools that should never be pruned
    core_tools = {
        "code_helper", "run_code", "web_search", "computer_settings", "file_read", "file_write", "file_list",
        "browser_open_url", "browser_execute_web_task", "browser_auto_navigate_and_extract",
        "browser_fill_and_submit_form", "browser_click", "browser_type", "browser_read_page",
        "qa_generate_report", "gmail_list_unread", "github_list_prs", "notion_search_pages"
    }
    
    for schema in TOOL_SCHEMAS:
        name = schema["name"]
        if name in core_tools:
            selected.append(schema)
            continue
            
        name_l = name.lower()
        desc = schema["description"].lower()
        name_parts = name_l.split("_")
        if any(part in prompt_lower for part in name_parts if len(part) > 2) or any(w in desc for w in prompt_lower.split() if len(w) > 4):
            selected.append(schema)

    if len(selected) < 3:
        return get_tool_prompt_block()

    schema_text = json.dumps(selected, indent=2)
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

**AUTO-ALLOW MODE**: All tools execute immediately without confirmation.

### Tool Definitions
{schema_text}
"""

