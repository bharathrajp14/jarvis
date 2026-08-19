# skills/builtin_extras.py — Advanced OS, DevSecOps, and System Skills for BR-JARVIS MK37
"""
Extra built-in skills for BR-JARVIS MK37.
Registers:
  - github_scan      — Scan, extract, and summarize GitHub repositories
  - screenshot_fix   — Capture screen, analyze error visually, and auto-fix source code
  - docker_deploy    — Build and deploy Docker containers
  - project_scaffold — Scaffold full multi-tier projects from prompt architecture
  - site_monitor     — Monitor website uptime, latency, and alert on outages
"""

from __future__ import annotations

from .loader import SkillDef, register_builtin_skill

_GITHUB_SCAN_PROMPT = """\
Analyze and summarize an open-source GitHub repository.

## Target Repository
$ARGUMENTS

## Execution Protocol
1. If full URL is given, fetch README via `fetch_page(url=...)` or `browser_auto_navigate_and_extract`.
2. Extract tech stack, architecture patterns, star counts, recent releases, and top issues.
3. Produce a structured repository breakdown table.
"""

_SCREENSHOT_FIX_PROMPT = """\
Capture screen visually, identify errors/stack traces, and apply auto-remediations.

## Context
$ARGUMENTS

## Execution Protocol
1. Capture the screen state using `take_screenshot`.
2. Locate error messages, traceback lines, and affected file paths.
3. Read the relevant source code via `file_read`.
4. Apply the targeted bug fix using `file_write` or `batch_file_ops`.
5. Verify syntax and report fixed error lines.
"""

_DOCKER_DEPLOY_PROMPT = """\
Build, containerize, and deploy Docker images and services.

## Deployment Goal
$ARGUMENTS

## Execution Protocol
1. Check Docker status via `run_code(code="import subprocess; print(subprocess.getoutput('docker --version'))")`.
2. Inspect or generate `Dockerfile` and `docker-compose.yml` with `file_write`.
3. Build container image and verify health status.
4. Report exposed ports and running container ID.
"""

_PROJECT_SCAFFOLD_PROMPT = """\
Scaffold a complete production-grade application architecture from description.

## Project Specification
$ARGUMENTS

## Execution Protocol
1. Initialize workspace directory layout via `init_project_workspace` or `batch_file_ops`.
2. Create config files (`pyproject.toml`, `requirements.txt` or `package.json`, `.env.template`, `README.md`).
3. Scaffold core source modules, entrypoints, and unit tests with `file_write`.
4. Verify project layout and report created component tree.
"""

_SITE_MONITOR_PROMPT = """\
Monitor website availability, HTTP status, and response latency.

## Target URL
$ARGUMENTS

## Execution Protocol
1. Inspect endpoint status and headers via `fetch_raw` or `headers_audit`.
2. Check response time and status code.
3. Set background monitoring if requested via `add_background_monitor`.
4. Return health report.
"""


def _register_extras() -> None:
    register_builtin_skill(
        SkillDef(
            name="github_scan",
            description="Scan, extract, and summarize any GitHub repository architecture and issues",
            triggers=["/github-scan", "/repo-scan", "scan github repo"],
            tools=["fetch_page", "fetch_raw", "browser_auto_navigate_and_extract", "web_search"],
            prompt=_GITHUB_SCAN_PROMPT,
            file_path="builtin:github_scan",
            category="engineering",
            domain="Open Source Intelligence",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="screenshot_fix",
            description="Capture screen, visually diagnose on-screen error, and patch source code",
            triggers=["/screenshot-fix", "/visual-debug", "fix screen error"],
            tools=["take_screenshot", "file_read", "file_write", "batch_file_ops", "run_code"],
            prompt=_SCREENSHOT_FIX_PROMPT,
            file_path="builtin:screenshot_fix",
            category="engineering",
            domain="Visual Debugging",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="docker_deploy",
            description="Build Dockerfiles, containerize applications, and manage containers",
            triggers=["/docker", "/containerize", "deploy docker"],
            tools=["run_code", "file_read", "file_write"],
            prompt=_DOCKER_DEPLOY_PROMPT,
            file_path="builtin:docker_deploy",
            category="engineering",
            domain="DevOps & Infrastructure",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="project_scaffold",
            description="Scaffold a production-grade full-stack codebase architecture from a prompt",
            triggers=["/scaffold", "/new-project", "create project structure"],
            tools=["init_project_workspace", "batch_file_ops", "file_write", "run_code"],
            prompt=_PROJECT_SCAFFOLD_PROMPT,
            file_path="builtin:project_scaffold",
            category="engineering",
            domain="Software Architecture",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="site_monitor",
            description="Check website uptime, response latency, and configure health monitoring",
            triggers=["/monitor-site", "/ping-site", "check website uptime"],
            tools=["fetch_raw", "headers_audit", "add_background_monitor", "web_search"],
            prompt=_SITE_MONITOR_PROMPT,
            file_path="builtin:site_monitor",
            category="productivity",
            domain="Site Reliability",
            user_invocable=True,
            source="builtin",
        )
    )


_register_extras()
