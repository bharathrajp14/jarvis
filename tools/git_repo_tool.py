# tools/git_repo_tool.py — Git Repository Controller Tool for JARVIS MK37
"""
Provides automated Git repository status inspection, diff generation, branch creation & switching,
commit staging, tag listing, and push/pull workflows.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from tools.registry import register_tool


def _run_git(args: list[str], cwd: str | Path = ".") -> tuple[int, str]:
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=15
        )
        return res.returncode, res.stdout.strip()
    except Exception as e:
        return -1, str(e)


@register_tool(
    name="git_repo_mgr",
    description="Inspect git repository status, view diffs/logs, switch branches, create branches, stage changes, create commits, and pull/push.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["status", "diff", "log", "branches", "create_branch", "checkout", "stage_all", "commit", "fetch", "pull", "push"],
                "description": "Git operation to perform"
            },
            "repo_dir": {"type": "string", "description": "Target repository directory path (default: current workspace)"},
            "commit_msg": {"type": "string", "description": "Commit message for 'commit' action"},
            "branch": {"type": "string", "description": "Branch name for 'checkout', 'create_branch', 'pull', or 'push'"}
        },
        "required": ["action"]
    }
)
def git_repo_mgr(args: dict) -> str:
    action = args.get("action", "status")
    repo_dir = Path(args.get("repo_dir", ".")).resolve()
    commit_msg = args.get("commit_msg", "Auto commit by BR JARVIS")
    branch = args.get("branch")

    code, out = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_dir)
    if code != 0 or out != "true":
        return f"Error: Directory '{repo_dir}' is not a valid Git repository."

    if action == "status":
        code, out = _run_git(["status", "--short", "--branch"], cwd=repo_dir)
        return f"📊 Git Repository Status ({repo_dir.name}):\n{out or 'Clean working tree. Nothing to commit.'}"

    elif action == "diff":
        code, out = _run_git(["diff", "HEAD"], cwd=repo_dir)
        if not out:
            return "ℹ️ No unstaged or staged diffs found."
        return f"📝 Git Diff:\n{out[:2500]}" + ("\n... (truncated)" if len(out) > 2500 else "")

    elif action == "log":
        code, out = _run_git(["log", "-n", "8", "--oneline", "--graph"], cwd=repo_dir)
        return f"📜 Recent Git Commit History:\n{out}"

    elif action == "branches":
        code, out = _run_git(["branch", "-a"], cwd=repo_dir)
        return f"🌿 Git Branches:\n{out}"

    elif action == "create_branch":
        if not branch:
            return "Error: 'branch' parameter required to create branch."
        code, out = _run_git(["checkout", "-b", branch], cwd=repo_dir)
        return f"🌿 Created & Switched to Branch '{branch}':\n{out}"

    elif action == "checkout":
        if not branch:
            return "Error: 'branch' parameter required for checkout."
        code, out = _run_git(["checkout", branch], cwd=repo_dir)
        return f"🌿 Checkout Output ({branch}):\n{out}"

    elif action == "stage_all":
        code, out = _run_git(["add", "-A"], cwd=repo_dir)
        return f"✅ Staged all changes in '{repo_dir.name}'."

    elif action == "commit":
        code, add_out = _run_git(["add", "-A"], cwd=repo_dir)
        code, out = _run_git(["commit", "-m", commit_msg], cwd=repo_dir)
        if code == 0:
            return f"✅ Git Commit Created:\n{out}"
        return f"❌ Commit failed or nothing to commit:\n{out}"

    elif action == "fetch":
        code, out = _run_git(["fetch", "--all"], cwd=repo_dir)
        return f"🔄 Git Fetch Output:\n{out or 'Up to date.'}"

    elif action == "pull":
        cmd = ["pull"]
        if branch:
            cmd.extend(["origin", branch])
        code, out = _run_git(cmd, cwd=repo_dir)
        return f"🔄 Git Pull Output:\n{out}"

    elif action == "push":
        cmd = ["push"]
        if branch:
            cmd.extend(["origin", branch])
        code, out = _run_git(cmd, cwd=repo_dir)
        return f"🚀 Git Push Output:\n{out}"

    return f"Unknown action '{action}'."
