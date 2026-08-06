# skills/builtin.py
"""
Built-in skills that ship with JARVIS MK37.
Importing this module registers all built-in skills into the loader.
"""
from __future__ import annotations
from skills.loader import SkillDef, register_builtin_skill


# ── /commit ────────────────────────────────────────────────────────────────

_COMMIT_PROMPT = """\
Review the current git state and create a well-structured commit.

## Steps

1. Run `git status` and `git diff --staged` to see what is staged.
   - If nothing is staged, run `git diff` to see unstaged changes, then stage relevant files.
2. Analyze the changes:
   - Summarize the nature of the change (feature, bug fix, refactor, docs, etc.)
   - Write a concise commit title (≤72 chars) focusing on *why*, not just *what*.
   - If multiple logical changes exist, ask the user whether to split them.
3. Create the commit:
   ```
   git commit -m "<title>"
   ```
   If additional context is needed, add a body separated by a blank line.
4. Print the commit hash and summary when done.

**Rules:**
- Never use `--no-verify`.
- Never commit files that likely contain secrets (.env, credentials, keys).
- Prefer imperative mood in the title: "Add X", "Fix Y", "Refactor Z".

User context: $ARGUMENTS
"""

_REVIEW_PROMPT = """\
Review the code or pull request and provide structured feedback.

## Steps

1. Understand the scope:
   - If a PR number or URL is given in $ARGUMENTS, use `gh pr view $ARGUMENTS --patch` to get the diff.
   - Otherwise, use `git diff main...HEAD` (or `git diff HEAD~1`) for local changes.
2. Analyze the diff:
   - Correctness: Are there bugs, edge cases, or logic errors?
   - Security: Injection, auth issues, exposed secrets, unsafe operations?
   - Performance: N+1 queries, unnecessary allocations, blocking calls?
   - Style: Does it follow existing conventions in the codebase?
   - Tests: Are new behaviors tested? Do existing tests cover the change?
3. Write a structured review:
   ```
   ## Summary
   One-line overview of what the change does.

   ## Issues
   - [CRITICAL/MAJOR/MINOR] Description and location

   ## Suggestions
   - Nice-to-have improvements

   ## Verdict
   APPROVE / REQUEST CHANGES / COMMENT
   ```
4. If changes are needed, list specific file:line references.

User context: $ARGUMENTS
"""

_EDIT_PROMPT = """\
You are an expert code editor. Edit files precisely as instructed.

## Task
$ARGUMENTS

## Rules
1. Read the target file first to understand its structure.
2. Make minimal, targeted changes — do NOT rewrite entire files.
3. Preserve all existing comments and formatting unrelated to your change.
4. After editing, verify the file is syntactically valid.
5. If editing Python, ensure PEP 8 compliance.
6. If editing JS/TS, ensure no syntax errors.
7. Report exactly what you changed and why.

## Available actions
- Use file_read to read the current content
- Use file_write to write the updated content
- Use run_code to validate syntax if needed
"""

_PC_CONTROL_PROMPT = """\
You are a PC automation specialist. Control the user's computer as instructed.

## Task
$ARGUMENTS

## Available actions
- cursor_move: Move mouse to coordinates (x, y)
- cursor_click: Click at position (left/right/double)
- keyboard_type: Type text at cursor position
- keyboard_hotkey: Key combinations (e.g., ctrl+c, alt+tab)
- keyboard_press: Single key press (enter, tab, escape, etc.)
- screen_find: AI-powered element finder (describe what to find)
- screen_click: Find and click an element by description
- clipboard_read / clipboard_write: Clipboard operations
- focus_window: Bring a window to the foreground
- take_screenshot: Capture the screen

## Rules
1. Always take a screenshot first to understand the current screen state.
2. Use screen_find to locate elements before clicking.
3. Add small waits between rapid actions to let the UI update.
4. Report what you did at each step.
"""

_WEB_RESEARCH_PROMPT = """\
Conduct thorough web research on the given topic and provide a comprehensive summary.

## Topic
$ARGUMENTS

## Steps
1. Search the web for the topic using multiple relevant queries.
2. Fetch and read the most promising results.
3. Synthesize the information into a well-structured report:
   - Overview / Definition
   - Key findings / Facts
   - Sources cited with URLs
4. If the user wants the results saved, write them to a file.

## Rules
- Use at least 2-3 different search queries to get comprehensive coverage.
- Cross-reference facts across multiple sources.
- Clearly separate facts from opinions.
- Always cite sources.
"""


_LIVE_OS_PROMPT = """\
You are an autonomous AI operating system controller with continuous visual perception ("Antigravity Mode").

## Task
$ARGUMENTS

## Available tools
- live_os_control: Launch autonomous perceive-plan-act loop on screen to complete the goal
- live_screen_analyze: Visual breakdown of screen content and open apps
- visual_click: Click any screen element by visual description
- visual_type: Type text into any vision-identified field
- visual_drag: Drag between elements by description

## Rules
1. Use live_os_control for multi-step desktop tasks requiring real-time visual reaction.
2. Provide step-by-step progress feedback.
"""


_AUDIT_PROMPT = """\
Perform an exhaustive code audit of the workspace or target directory.

## Steps
1. Use `code_refactor` (action="analyze_ast") or `file_list` to inspect workspace structure.
2. Check for syntax errors, bare exceptions, unused imports, or security anti-patterns.
3. Generate a structured audit report summarizing code health, complexity, and refactoring targets.

User context: $ARGUMENTS
"""

_OPTIMIZE_PROMPT = """\
Audit and optimize operating system performance and memory allocation.

## Steps
1. Run `system_diagnostic` (aspect="full_summary") and aspect="top_processes" to check RAM/CPU.
2. Run `system_cleanup` or identify temporary log files / cache files to purge.
3. Summarize memory reclaimed and system health metrics.

User context: $ARGUMENTS
"""

_TESTRUN_PROMPT = """\
Discover and run unit test suites in the workspace.

## Steps
1. Search for test files using `file_list` or `batch_file_ops`.
2. Run tests via `run_code` or pytest CLI.
3. Report test status, passed/failed counts, and error tracebacks.

User context: $ARGUMENTS
"""


def _register_builtins() -> None:
    """Register all built-in skills."""

    register_builtin_skill(SkillDef(
        name="live_os",
        description="Autonomous live OS visual control ('Antigravity Mode') with real-time perception and fast reaction loop",
        triggers=["/live-control", "/os-control", "/screen-react", "/live-os"],
        tools=["live_os_control", "live_screen_analyze", "visual_click", "visual_type", "visual_drag"],
        prompt=_LIVE_OS_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants full autonomous visual control over the operating system desktop.",
        argument_hint="<goal or task on desktop>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="commit",
        description="Review staged changes and create a well-structured git commit",
        triggers=["/commit"],
        tools=["run_code", "file_read"],
        prompt=_COMMIT_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to commit changes. Triggers: '/commit', 'commit changes'.",
        argument_hint="[optional context]",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="review",
        description="Review code changes or a pull request and provide structured feedback",
        triggers=["/review", "/review-pr"],
        tools=["run_code", "file_read", "web_search"],
        prompt=_REVIEW_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants a code review. Triggers: '/review', '/review-pr'.",
        argument_hint="[PR number or URL]",
        arguments=["pr"],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="edit",
        description="Precisely edit files in the workspace with minimal changes",
        triggers=["/edit"],
        tools=["file_read", "file_write", "run_code"],
        prompt=_EDIT_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to edit a specific file or make code changes.",
        argument_hint="<file path> <what to change>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="pc_control",
        description="Control mouse, keyboard, and screen elements on the user's PC",
        triggers=["/pc", "/control"],
        tools=["cursor_move", "cursor_click", "keyboard_type", "keyboard_hotkey",
               "keyboard_press", "screen_find", "screen_click", "take_screenshot",
               "focus_window", "clipboard_read", "clipboard_write"],
        prompt=_PC_CONTROL_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants to automate mouse/keyboard/screen interactions.",
        argument_hint="<what to do on screen>",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="research",
        description="Deep web research with multi-query coverage and source citations",
        triggers=["/research", "/web-research"],
        tools=["web_search", "fetch_page", "fetch_raw", "file_write"],
        prompt=_WEB_RESEARCH_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when the user wants comprehensive research on a topic.",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="audit",
        description="Perform comprehensive codebase security, AST structure, and dead code analysis",
        triggers=["/audit", "/code-audit"],
        tools=["code_refactor", "file_list", "file_read"],
        prompt=_AUDIT_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when auditing codebase quality or searching for vulnerabilities.",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="optimize",
        description="Optimize system performance, reclaim memory, and clean cache",
        triggers=["/optimize", "/clean-system"],
        tools=["system_diagnostic", "system_cleanup"],
        prompt=_OPTIMIZE_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when tuning operating system performance or cleaning system memory.",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    register_builtin_skill(SkillDef(
        name="testrun",
        description="Discover, execute, and report results for project test suites",
        triggers=["/testrun", "/run-tests"],
        tools=["run_code", "file_list", "batch_file_ops"],
        prompt=_TESTRUN_PROMPT,
        file_path="<builtin>",
        when_to_use="Use when running automated tests across the workspace.",
        arguments=[],
        user_invocable=True,
        context="inline",
        source="builtin",
    ))

    try:
        from skills.builtin_connectors import load_builtin_connector_skills
        for c_skill in load_builtin_connector_skills():
            register_builtin_skill(c_skill)
    except Exception as ex:
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[Skills] Warning loading connector skills: {ex}" }" if isinstance(f"[Skills] Warning loading connector skills: {ex}", str) else f"[Skills] Warning loading connector skills: {ex}")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[Skills] Warning loading connector skills: {ex}" }" if isinstance(f"[Skills] Warning loading connector skills: {ex}", str) else f"[Skills] Warning loading connector skills: {ex}")


_register_builtins()
