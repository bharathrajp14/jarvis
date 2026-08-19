# tools/scratchpad_tools.py — Scratchpad Tools Plugin for JARVIS MK37
"""
Exposes dynamic scratchpad workspace operations as tools.
"""

from __future__ import annotations

from brjarvis.agent.scratchpad import get_scratchpad

from .registry import register_tool


@register_tool(
    name="scratchpad_write",
    description="Write content or code to a scratch file in ./scratch/ for temporary work or evaluation.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Filename in scratch directory (e.g., test_script.py, notes.md)"},
            "content": {"type": "string", "description": "Content or code to write"},
        },
        "required": ["name", "content"],
    },
)
def tool_scratchpad_write(args: dict) -> str:
    sp = get_scratchpad()
    return sp.write_file(args["name"], args["content"])


@register_tool(
    name="scratchpad_read",
    description="Read content from a scratch file in ./scratch/.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Filename in scratch directory to read"},
        },
        "required": ["name"],
    },
)
def tool_scratchpad_read(args: dict) -> str:
    sp = get_scratchpad()
    return sp.read_file(args["name"])


@register_tool(
    name="scratchpad_eval",
    description="Execute a code snippet or script in ./scratch/ and capture stdout/stderr and returncode.",
    parameters={
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "Scratch filename or raw code snippet"},
            "language": {"type": "string", "description": "Language: python, node, powershell, bash (default: python)"},
            "timeout": {"type": "integer", "description": "Execution timeout in seconds (default: 30)"},
        },
        "required": ["script"],
    },
)
def tool_scratchpad_eval(args: dict) -> str:
    sp = get_scratchpad()
    script = args["script"]
    lang = args.get("language", "python")
    timeout = args.get("timeout", 30)

    res = sp.eval_script(script, language=lang, timeout=timeout)
    if not res["success"]:
        err_msg = res.get("error") or res.get("stderr") or "Unknown execution failure"
        return f"[Scratchpad Eval Failed ({res['execution_ms']}ms)]:\nReturncode: {res.get('returncode')}\nError:\n{err_msg}\nStdout:\n{res.get('stdout', '')}"

    stdout = res.get("stdout", "").strip()
    stderr = res.get("stderr", "").strip()
    out = f"[Scratchpad Eval Success ({res['execution_ms']}ms)]\n"
    if stdout:
        out += f"Output:\n{stdout}\n"
    if stderr:
        out += f"Stderr:\n{stderr}\n"
    if not stdout and not stderr:
        out += "Output: (no stdout/stderr output)"
    return out.strip()


@register_tool(
    name="scratchpad_list", description="List active temporary files in the ./scratch/ workspace.", parameters={}
)
def tool_scratchpad_list(args: dict) -> str:
    sp = get_scratchpad()
    files = sp.list_files()
    if not files:
        return "Scratchpad workspace is currently empty."
    lines = [f"Scratchpad Files ({len(files)}):"]
    for f in files:
        lines.append(f"  • {f['name']} ({f['size_bytes']} bytes, modified {f['modified']})")
    return "\n".join(lines)


@register_tool(name="scratchpad_clear", description="Clean temporary scratch workspace files and notes.", parameters={})
def tool_scratchpad_clear(args: dict) -> str:
    sp = get_scratchpad()
    return sp.clear()
