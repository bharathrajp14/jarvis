# skills/builtin_editor.py — BR-JARVIS MK37 Editor and Code Manipulation Skills
"""
Built-in editor skills for BR-JARVIS MK37.
Combines filesystem and AST refactoring tools with PC control to operate code editors
(VS Code, Cursor, etc.) autonomously.
"""

from __future__ import annotations

from .loader import SkillDef, register_builtin_skill

_EDITOR_OPEN_PROMPT = """\
Open a file or project directory in the user's code editor.

## Target
$ARGUMENTS

## Execution Protocol
1. Determine full file or directory path.
2. Use `open_workspace_file(file_path=...)` or `open_app` to launch in VS Code / Cursor / default IDE.
3. Bring editor window to focus using `focus_window`.
"""

_EDITOR_GOTO_PROMPT = """\
Navigate to a specific line, symbol, or file in the active editor.

## Target
$ARGUMENTS

## Execution Protocol
1. Focus the editor window with `focus_window`.
2. Use keyboard shortcuts:
   - Go to Line: `keyboard_hotkey(keys="ctrl+g")` -> `keyboard_type(text="<line_number>")` -> `keyboard_press(key="enter")`
   - Go to Symbol: `keyboard_hotkey(keys="ctrl+shift+o")` -> `keyboard_type(text="<symbol>")`
   - Quick Open File: `keyboard_hotkey(keys="ctrl+p")` -> `keyboard_type(text="<filename>")`
"""

_SMART_PATCH_PROMPT = """\
Perform an AST-level syntax rewrite or structural code refactoring on a target file.

## Refactoring Goal
$ARGUMENTS

## Execution Protocol
1. Read the target file with `file_read`.
2. Apply AST-aware refactorings using `code_refactor(action="refactor", file_path=..., ...)` or apply minimal patches via `file_write`.
3. Verify syntax correctness using `run_code(code="import py_compile; py_compile.compile('<file_path>', doraise=True)")`.
4. Report changes made.
"""

_FORMAT_LINT_PROMPT = """\
Format, lint, and clean up style across workspace files.

## Target Scope
$ARGUMENTS

## Execution Protocol
1. Identify target files via `file_list` or `fast_file_search`.
2. Run formatters / linters using `run_code` (e.g. `ruff format` or `black` / `prettier`).
3. Report formatted files and any remaining lint diagnostics.
"""


def _register_editor_builtins() -> None:
    register_builtin_skill(
        SkillDef(
            name="editor_open",
            description="Open a file or directory in the code editor (VS Code, Cursor, etc.)",
            triggers=["/editor-open", "/open-in-editor", "open in editor"],
            tools=["open_workspace_file", "open_app", "focus_window"],
            prompt=_EDITOR_OPEN_PROMPT,
            file_path="builtin:editor_open",
            category="engineering",
            domain="Editor Control",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="editor_goto",
            description="Navigate to a specific line, class, or symbol in the active editor",
            triggers=["/editor-goto", "/goto-symbol", "/goto-line"],
            tools=["focus_window", "keyboard_hotkey", "keyboard_type", "keyboard_press"],
            prompt=_EDITOR_GOTO_PROMPT,
            file_path="builtin:editor_goto",
            category="engineering",
            domain="Editor Control",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="smart_patch",
            description="Perform AST-aware syntax refactoring and precise code modifications",
            triggers=["/smart-patch", "/ast-refactor", "/code-patch"],
            tools=["code_refactor", "file_read", "file_write", "batch_file_ops", "run_code"],
            prompt=_SMART_PATCH_PROMPT,
            file_path="builtin:smart_patch",
            category="engineering",
            domain="Code Refactoring",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="format_lint",
            description="Auto-format and lint code files across the workspace",
            triggers=["/format", "/lint", "/clean-code"],
            tools=["run_code", "file_list", "batch_file_ops"],
            prompt=_FORMAT_LINT_PROMPT,
            file_path="builtin:format_lint",
            category="engineering",
            domain="Code Quality",
            user_invocable=True,
            source="builtin",
        )
    )


_register_editor_builtins()
