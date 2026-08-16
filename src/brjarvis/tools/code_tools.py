# tools/code_tools.py — JARVIS MK37 Code Sandbox Tools Plugin
"""
Code execution/sandbox tools plugin for JARVIS MK37. Contains run_code.
"""
from __future__ import annotations

import json
from .registry import register_tool
from .sandbox import CodeSandbox

_sandbox = CodeSandbox()


@register_tool(
    name="run_code",
    description="Execute code in a sandboxed environment. Supports python, javascript, bash.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The code to execute"},
            "lang": {"type": "string", "description": "Language: python, javascript, bash (default: python)"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
        },
        "required": ["code"],
    }
)
def tool_run_code(args: dict) -> str:
    code = args["code"]
    lang = args.get("lang", "python")
    timeout = args.get("timeout", 30)
    result = _sandbox.run(code=code, lang=lang, timeout=timeout)
    return json.dumps(result, indent=2)
