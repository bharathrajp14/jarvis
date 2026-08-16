# tools/code_refactor_tool.py — AST Analysis & Code Refactoring Tool for JARVIS MK37
"""
Provides python code analysis, AST parsing, syntax validation, refactoring suggestions,
and code formatting tools.
"""
from __future__ import annotations

import ast
import sys
import traceback
from pathlib import Path
from .registry import register_tool


@register_tool(
    name="code_refactor",
    description="Analyze, validate syntax, format, or refactor source code files using Python AST and linter checks.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_syntax", "analyze_ast", "format_imports", "suggest_refactor"],
                "description": "Refactoring action to perform"
            },
            "file_path": {"type": "string", "description": "Target source code file path"},
            "code": {"type": "string", "description": "Optional inline code snippet to check"}
        },
        "required": ["action"]
    }
)
def code_refactor(args: dict) -> str:
    action = args.get("action", "check_syntax")
    file_path = args.get("file_path")
    code = args.get("code")

    if not code and file_path:
        p = Path(file_path)
        if not p.exists():
            return f"Error: File '{file_path}' does not exist."
        try:
            code = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading file '{file_path}': {e}"

    if not code:
        return "Error: Neither file_path nor code content was provided."

    if action == "check_syntax":
        try:
            ast.parse(code)
            return "✅ Syntax Check Passed: Code is syntactically valid."
        except SyntaxError as se:
            return (
                f"❌ Syntax Error on Line {se.lineno}, Col {se.offset}:\n"
                f"Line: {se.text}\n"
                f"Detail: {se.msg}"
            )

    elif action == "analyze_ast":
        try:
            tree = ast.parse(code)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            async_funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(f"{node.module}")

            return (
                f"📊 AST Analysis Results:\n"
                f"- Classes ({len(classes)}): {', '.join(classes) or 'None'}\n"
                f"- Functions ({len(functions)}): {', '.join(functions) or 'None'}\n"
                f"- Async Functions ({len(async_funcs)}): {', '.join(async_funcs) or 'None'}\n"
                f"- Imported Modules ({len(imports)}): {', '.join(set(imports)) or 'None'}"
            )
        except Exception as e:
            return f"AST Analysis Error: {e}"

    elif action == "format_imports":
        try:
            lines = code.splitlines()
            imports = [l for l in lines if l.startswith("import ") or l.startswith("from ")]
            others = [l for l in lines if not (l.startswith("import ") or l.startswith("from "))]
            sorted_imports = sorted(list(set(imports)))
            formatted_code = "\n".join(sorted_imports) + "\n\n" + "\n".join(others)
            
            if file_path:
                Path(file_path).write_text(formatted_code, encoding="utf-8")
                return f"✅ Formatted and sorted imports in '{file_path}'."
            return f"✅ Formatted Code Preview:\n\n{formatted_code[:1000]}"
        except Exception as e:
            return f"Import formatting failed: {e}"

    elif action == "suggest_refactor":
        suggestions = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) > 50:
                        suggestions.append(f"⚠️ Function '{node.name}' is too long ({len(node.body)} statements). Consider breaking it down.")
                    if len(node.args.args) > 6:
                        suggestions.append(f"⚠️ Function '{node.name}' has too many arguments ({len(node.args.args)}). Consider using a dataclass or dict.")
                elif isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        suggestions.append(f"⚠️ Bare 'except:' clause found near line {node.lineno}. Catch specific exceptions.")
            
            if not suggestions:
                return "✅ No obvious code smells or refactoring flags found."
            return "💡 Refactoring Suggestions:\n" + "\n".join(suggestions)
        except Exception as e:
            return f"Refactoring check failed: {e}"

    return f"Unknown action '{action}'."
