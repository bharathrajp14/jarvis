# tools/code_tools.py — BR JARVIS Sandboxed Code Execution Suite
"""
High-Fidelity Sandboxed Code Execution Suite for BR JARVIS MK40.2 / MK41.
Provides isolated execution, environment filtering, stdout/stderr capture,
and canonical ToolResult evidence contracts.
"""

from __future__ import annotations

from .domain import ToolErrorCode
from .registry import register_tool
from .sandbox import CodeSandbox
from .tool_result import ToolResult

_sandbox = CodeSandbox()


@register_tool(
    name="run_code",
    description="Execute code in an isolated sandbox environment. Supports python, javascript, bash, powershell. Args: 'code' (source code string), 'lang' (language, default: 'python'), 'timeout' (seconds, default: 30).",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Source code to execute"},
            "lang": {
                "type": "string",
                "enum": ["python", "javascript", "bash", "powershell"],
                "description": "Programming language (default: python)",
            },
            "timeout": {"type": "integer", "description": "Execution timeout in seconds (default: 30)"},
        },
        "required": ["code"],
    },
    category="code",
    risk_level="high",
    permission_required="LOCAL_SYSTEM",
    is_read_only=False,
    idempotent=False,
    verification_strategy="PROCESS_RUNNING",
)
def tool_run_code(args: dict) -> ToolResult:
    """Execute source code inside isolated sandbox."""
    code = str(args.get("code", "")).strip()
    if not code:
        return ToolResult.failed("run_code", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'code' is required.")

    lang = str(args.get("lang", "python")).strip().lower() or "python"
    timeout = int(args.get("timeout", 30))

    try:
        raw_res = _sandbox.run(code=code, lang=lang, timeout=timeout)
        success = raw_res.get("success", False)
        stdout = raw_res.get("stdout", "")
        stderr = raw_res.get("stderr", "")
        ret_code = raw_res.get("returncode", 0)
        evidence = f"Executed {lang} snippet (Exit code: {ret_code})"

        if success or ret_code == 0:
            return ToolResult.success(
                tool_name="run_code",
                data=raw_res,
                output=stdout or "(Execution completed with no output)",
                evidence=evidence,
                verified=True,
                artifacts=raw_res.get("artifacts", []),
                metadata={"lang": lang, "return_code": ret_code},
            )
        else:
            return ToolResult.failed(
                tool_name="run_code",
                error_code=ToolErrorCode.EXECUTION_EXCEPTION,
                message=raw_res.get("error") or stderr or f"Process exited with code {ret_code}",
                stderr=stderr,
                return_code=ret_code,
                data=raw_res,
            )
    except Exception as e:
        return ToolResult.failed(
            tool_name="run_code",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Code execution exception: {e}",
        )
