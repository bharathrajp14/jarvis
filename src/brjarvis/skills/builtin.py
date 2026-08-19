# skills/builtin.py — Core Built-in Skills for BR-JARVIS MK37
"""
Built-in core skills that ship natively with BR-JARVIS MK37.
Importing this module registers all built-in skills into the loader.
"""

from __future__ import annotations

import logging

from .loader import SkillDef, register_builtin_skill

logger = logging.getLogger("JARVIS.Skills.Builtin")


# ── /live-control & /live-os ──────────────────────────────────────────────────

_LIVE_OS_PROMPT = """\
You are an autonomous AI operating system controller with continuous visual perception ("Antigravity Live OS Mode").

## Task Goal
$ARGUMENTS

## Available Tools
- `live_os_control`: Launch the autonomous perceive-plan-act loop on screen to achieve the task.
- `live_screen_analyze`: Visual breakdown and OCR of screen content, active windows, and controls.
- `visual_click`: Click any screen UI element by visual description (e.g. "Save button in top toolbar").
- `visual_type`: Type text directly into an element identified by visual description.
- `visual_drag`: Drag between screen elements by visual descriptions.
- `take_screenshot`: Capture full desktop image for visual verification.
- `focus_window`: Bring target application window to foreground.

## Autonomous Execution Rules
1. First capture screen state or use `live_os_control` to initiate the task workflow.
2. Verify visual results before claiming completion.
3. Handle dialogs, permission prompts, or confirmation modals adaptively.
4. Report clear step-by-step progress and final state.
"""


# ── /commit ───────────────────────────────────────────────────────────────────

_COMMIT_PROMPT = """\
Review the current git state and create a high-precision, well-structured git commit.

## Task
$ARGUMENTS

## Execution Protocol
1. **Inspect Workspace Diff**:
   - Use `run_code` or `git_repo_mgr` to check `git status --short` and `git diff`.
   - Identify modified, added, and deleted files.
2. **Security & Cleanliness Check**:
   - Verify NO secrets, API keys, `.env` files, or binary artifacts are staged.
3. **Draft Semantic Commit Message**:
   - Format: `<type>(<scope>): <concise imperative summary>` (max 72 chars).
   - Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `security`.
   - If multiple distinct changes exist, group them logically.
4. **Execute Commit**:
   - Stage appropriate files: `git add <files>`
   - Commit: `git commit -m "<title>" -m "<body>"`
5. **Verify**:
   - Run `git log -1 --stat` to verify the commit hash and committed files.

User Context: $ARGUMENTS
"""


# ── /review ───────────────────────────────────────────────────────────────────

_REVIEW_PROMPT = """\
Perform an exhaustive architectural and security code review of files or changes.

## Task
$ARGUMENTS

## Review Protocol
1. **Examine Source Code & Diffs**:
   - Use `file_read` to inspect files or `run_code` with `git diff` to view pending changes.
2. **Multi-Dimensional Analysis**:
   - **Correctness & Edge Cases**: Off-by-one errors, null/None exceptions, async race conditions, unhandled exceptions.
   - **Security**: SQL injection, command injection, secret leakage, unvalidated inputs, prompt injection.
   - **Performance**: Blocking I/O in async loops, O(N²) iterations, redundant re-computations, memory leaks.
   - **Style & Architecture**: SOLID principles, modularity, type hints, PEP 8 / TypeScript conventions.
3. **Structured Review Deliverable**:
   Format the review report:
   ```markdown
   ## 🛡️ Code Review Report
   ### Summary
   <1-2 sentence executive overview>

   ### Findings & Risk Assessment
   | Severity | File:Line | Issue | Recommended Fix |
   | :--- | :--- | :--- | :--- |
   | 🔴 CRITICAL | `path/to/file.py:42` | Description | Fix recommendation |
   | 🟡 MAJOR | `path/to/file.py:88` | Description | Fix recommendation |
   | 🟢 MINOR | `path/to/file.py:12` | Description | Fix recommendation |

   ### Verdict
   [APPROVE / REQUEST REVISIONS / COMMENTS]
   ```
"""


# ── /edit ─────────────────────────────────────────────────────────────────────

_EDIT_PROMPT = """\
You are an expert code refactorer and editor. Make targeted, surgical modifications to workspace files.

## Target Modification
$ARGUMENTS

## Protocol
1. **Read Target File**: Use `file_read` or `open_workspace_file` to inspect the exact lines and existing style.
2. **Plan Minimal Patch**: Modify only the necessary functions or blocks without introducing collateral regressions.
3. **Write Changes**: Use `file_write` or `batch_file_ops` to write the updated file content.
4. **Syntax Verification**: Run `run_code` with `python -m py_compile <file>` to ensure 0 syntax errors.
5. **Report**: Output a concise diff or summary of changes made.
"""


# ── /pc & /control ────────────────────────────────────────────────────────────

_PC_CONTROL_PROMPT = """\
You are a PC automation specialist. Control keyboard, mouse, and desktop UI elements.

## Task Goal
$ARGUMENTS

## Available Actions
- `cursor_move`: Move mouse to coordinates (x, y).
- `cursor_click`: Click at target location (left, right, double).
- `keyboard_type`: Type text into the focused field.
- `keyboard_hotkey`: Trigger key combinations (e.g. 'ctrl+s', 'alt+tab', 'win+r').
- `keyboard_press`: Press single keys ('enter', 'tab', 'escape').
- `screen_find`: Locate UI elements visually by description.
- `screen_click`: Find and click an element by visual description.
- `take_screenshot`: Capture the current screen state.
- `focus_window`: Bring an application window to the foreground.
- `clipboard_read` / `clipboard_write`: Manage clipboard contents.

## Execution Rules
1. Always take a screenshot or locate the target UI element before sending clicks.
2. Allow short pauses for OS animations and window loading.
3. Verify that the UI responded to the input.
"""


# ── /research & /web-research ─────────────────────────────────────────────────

_WEB_RESEARCH_PROMPT = """\
Conduct deep, multi-source web intelligence research on the specified topic.

## Research Topic
$ARGUMENTS

## Execution Protocol
1. **Multi-Query Discovery**: Execute 2-3 targeted searches via `web_search` covering market trends, technical architecture, and real-world benchmarks.
2. **Deep Content Extraction**: Use `fetch_page` or `browser_auto_navigate_and_extract` to read the primary documentation, whitepapers, or articles.
3. **Fact Verification**: Cross-reference key statistics and claims across multiple citations.
4. **Structured Research Deliverable**:
   - Executive Summary (key breakthroughs & metrics)
   - Architectural / Technical Breakdown
   - Comparison Matrix Table
   - Verified Source Citations with URLs
"""


# ── /audit & /code-audit ──────────────────────────────────────────────────────

_AUDIT_PROMPT = """\
Perform an exhaustive codebase quality, AST syntax, and security vulnerability audit.

## Task
$ARGUMENTS

## Audit Protocol
1. **Workspace Scanning**: Call `audit_codebase` or `file_list` to inventory project files and directories.
2. **AST & Syntax Health**: Scan for syntax errors, bare exceptions, unused imports, or broken imports.
3. **Security Vulnerability Scan**: Call `audit_prompt_security` and check for exposed secrets, unsafe `eval()`, or unvalidated shell executions.
4. **Deliverable**: Return an Executive Code Health Audit summarizing:
   - Total files analyzed & health score
   - Critical vulnerabilities with remediation patches
   - Dead code and refactoring opportunities
"""


# ── /optimize & /clean-system ─────────────────────────────────────────────────

_OPTIMIZE_PROMPT = """\
Audit, tune, and optimize system memory, processes, and workspace cache.

## Task
$ARGUMENTS

## Optimization Protocol
1. **Inspect Diagnostics**: Call `get_system_diagnostics` or `system_diagnostic` to retrieve CPU, RAM, disk metrics, and top memory-consuming processes.
2. **Purge Cache & Temp Files**: Call `system_cleanup` or identify temporary cache files, `.pyc`, and log artifacts to safely remove.
3. **Process Optimization**: Identify unresponsive or runaway background processes and report them.
4. **Summary**: Provide a clean breakdown of reclaimed memory, storage freed, and system health status.
"""


# ── /testrun & /run-tests ─────────────────────────────────────────────────────

_TESTRUN_PROMPT = """\
Discover, execute, and verify automated test suites across the workspace.

## Task
$ARGUMENTS

## Execution Protocol
1. **Discover Tests**: Find all test files using `file_list` or `fast_file_search` (patterns: `test_*.py`, `*_test.py`).
2. **Execute Test Runner**: Use `run_code` to execute `pytest -v` or target specific test files.
3. **Diagnose Failures**: For any failing test case, inspect the stack trace, read the failing test and source file, and pinpoint the exact root cause.
4. **Deliverable**: Summarize total tests run, passed/failed count, execution duration, and actionable fix recommendations.
"""


def _register_builtins() -> None:
    """Register all built-in core skills."""

    register_builtin_skill(
        SkillDef(
            name="live_os",
            description="Autonomous live OS visual control ('Antigravity Mode') with real-time perception and fast reaction loop",
            triggers=["/live-control", "/os-control", "/screen-react", "/live-os"],
            tools=[
                "live_os_control",
                "live_screen_analyze",
                "visual_click",
                "visual_type",
                "visual_drag",
                "take_screenshot",
                "focus_window",
            ],
            prompt=_LIVE_OS_PROMPT,
            file_path="<builtin:live_os>",
            category="general",
            domain="OS Automation",
            when_to_use="Use when the user wants full autonomous visual control over the operating system desktop.",
            argument_hint="<goal or task on desktop>",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="commit",
            description="Review staged changes, check secrets, and create a well-structured git commit",
            triggers=["/commit", "/git-commit", "commit changes"],
            tools=["run_code", "git_repo_mgr", "file_read", "file_list"],
            prompt=_COMMIT_PROMPT,
            file_path="<builtin:commit>",
            category="engineering",
            domain="Version Control",
            when_to_use="Use when the user wants to commit changes to git repository.",
            argument_hint="[optional context / commit message hint]",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="review",
            description="Perform deep architectural, security, and quality code review of changes or pull requests",
            triggers=["/review", "/review-pr", "/code-review"],
            tools=["file_read", "file_list", "run_code", "web_search"],
            prompt=_REVIEW_PROMPT,
            file_path="<builtin:review>",
            category="engineering",
            domain="Code Quality",
            when_to_use="Use when the user wants a code review on files, PRs, or git diffs.",
            argument_hint="[file path, PR number, or diff scope]",
            arguments=["scope"],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="edit",
            description="Precisely edit files in the workspace with minimal changes and syntax verification",
            triggers=["/edit", "/modify-file", "/code-edit"],
            tools=["file_read", "file_write", "open_workspace_file", "batch_file_ops", "run_code"],
            prompt=_EDIT_PROMPT,
            file_path="<builtin:edit>",
            category="engineering",
            domain="Code Editing",
            when_to_use="Use when the user wants to edit a specific file or make code changes.",
            argument_hint="<file path> <what to change>",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="pc_control",
            description="Control mouse, keyboard, clipboard, and screen elements on the user's PC",
            triggers=["/pc", "/control", "/desktop-action"],
            tools=[
                "cursor_move",
                "cursor_click",
                "keyboard_type",
                "keyboard_hotkey",
                "keyboard_press",
                "screen_find",
                "screen_click",
                "take_screenshot",
                "focus_window",
                "clipboard_read",
                "clipboard_write",
            ],
            prompt=_PC_CONTROL_PROMPT,
            file_path="<builtin:pc_control>",
            category="general",
            domain="PC Automation",
            when_to_use="Use when the user wants to automate mouse/keyboard/screen interactions.",
            argument_hint="<what to do on screen>",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="research",
            description="Deep web intelligence research with multi-query coverage and source citations",
            triggers=["/research", "/web-research", "/deep-search"],
            tools=["web_search", "fetch_page", "fetch_raw", "browser_auto_navigate_and_extract", "file_write"],
            prompt=_WEB_RESEARCH_PROMPT,
            file_path="<builtin:research>",
            category="research",
            domain="Web Intelligence",
            when_to_use="Use when the user wants comprehensive research on a topic.",
            argument_hint="<topic to research>",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="audit",
            description="Perform comprehensive codebase security, AST structure, and vulnerability analysis",
            triggers=["/audit", "/code-audit", "/security-audit"],
            tools=["audit_codebase", "audit_prompt_security", "code_refactor", "file_list", "file_read"],
            prompt=_AUDIT_PROMPT,
            file_path="<builtin:audit>",
            category="engineering",
            domain="Security & Audit",
            when_to_use="Use when auditing codebase quality or searching for vulnerabilities.",
            argument_hint="[target directory or component]",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="optimize",
            description="Optimize system performance, reclaim RAM/CPU, and clean cache",
            triggers=["/optimize", "/clean-system", "/system-tune"],
            tools=["get_system_diagnostics", "system_diagnostic", "system_cleanup", "system_optimizer", "kill_process"],
            prompt=_OPTIMIZE_PROMPT,
            file_path="<builtin:optimize>",
            category="general",
            domain="System Performance",
            when_to_use="Use when tuning operating system performance or cleaning system memory.",
            argument_hint="[optional target aspect: memory, disk, processes]",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="testrun",
            description="Discover, execute, and report results for project test suites",
            triggers=["/testrun", "/run-tests", "/pytest"],
            tools=["run_code", "file_list", "batch_file_ops", "fast_file_search"],
            prompt=_TESTRUN_PROMPT,
            file_path="<builtin:testrun>",
            category="engineering",
            domain="Testing & QA",
            when_to_use="Use when running automated tests across the workspace.",
            argument_hint="[test path or filter keyword]",
            arguments=[],
            user_invocable=True,
            context="inline",
            source="builtin",
        )
    )

    # Register built-in connector skills
    try:
        from .builtin_connectors import load_builtin_connector_skills

        for c_skill in load_builtin_connector_skills():
            register_builtin_skill(c_skill)
    except Exception as ex:
        logger.debug("[Skills] Notice loading connector skills: %s", ex)


_register_builtins()
