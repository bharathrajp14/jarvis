# tools/git_repo_tool.py — Git Repository Controller Tool for BR JARVIS MK40.2
"""
Provides automated Git repository status inspection, diff generation, branch creation & switching,
commit staging, tag listing, and push/pull workflows.

MK40.2 changes:
- Uses WorkspaceManager to resolve all repo_dir paths (prevents workspace/workspace/ bug)
- Git push verification: checks returncode AND verifies remote branch via ls-remote
- Returns structured evidence strings for the ExecutionLedger
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .registry import register_tool


def _run_git(args: list[str], cwd: str | Path = ".") -> tuple[int, str]:
    try:
        res = subprocess.run(
            ["git"] + args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30
        )
        return res.returncode, res.stdout.strip()
    except Exception as e:
        return -1, str(e)


def _resolve_repo_dir(raw_path: str | None) -> Path:
    """
    Resolve repo_dir using WorkspaceManager to prevent path duplication bugs.
    Falls back to workspace root if no path given.
    """
    try:
        from brjarvis.core.paths import get_workspace_manager

        wm = get_workspace_manager()
        if not raw_path or raw_path in (".", "./"):
            return wm.workspace_root
        return wm.resolve_workspace_path(raw_path)
    except Exception:
        # Fallback: resolve relative to cwd
        return Path(raw_path or ".").resolve()


@register_tool(
    name="git_repo_mgr",
    description="Inspect git repository status, view diffs/logs, switch branches, create branches, stage changes, create commits, and pull/push. Returns structured evidence for verification.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "status",
                    "diff",
                    "log",
                    "branches",
                    "create_branch",
                    "checkout",
                    "stage_all",
                    "commit",
                    "fetch",
                    "pull",
                    "push",
                    "verify_remote",
                ],
                "description": "Git operation to perform",
            },
            "repo_dir": {"type": "string", "description": "Target repository directory path (default: workspace root)"},
            "commit_msg": {"type": "string", "description": "Commit message for 'commit' action"},
            "branch": {
                "type": "string",
                "description": "Branch name for 'checkout', 'create_branch', 'pull', or 'push'",
            },
        },
        "required": ["action"],
    },
)
def git_repo_mgr(args: dict) -> str:
    action = args.get("action", "status")
    repo_dir = _resolve_repo_dir(args.get("repo_dir"))
    commit_msg = args.get("commit_msg", "Auto commit by BR JARVIS")
    branch = args.get("branch")

    # Validate this is a git repo
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
        if code != 0:
            return f"❌ Stage failed (returncode {code}):\n{out}"
        return f"✅ Staged all changes in '{repo_dir.name}'."

    elif action == "commit":
        code_add, out_add = _run_git(["add", "-A"], cwd=repo_dir)
        code, out = _run_git(["commit", "-m", commit_msg], cwd=repo_dir)
        if code == 0:
            # Extract commit hash for evidence
            _, hash_out = _run_git(["rev-parse", "HEAD"], cwd=repo_dir)
            return f"✅ Git Commit Created (hash: {hash_out[:12]}):\n{out}"
        return f"❌ Commit failed or nothing to commit (returncode {code}):\n{out}"

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

        # MK40.2 §16: Push verification — tool success ≠ GitHub push success
        if code != 0:
            return (
                f"❌ Git Push FAILED (returncode {code}):\n{out}\n"
                f"[EVIDENCE: push returncode={code}, branch={branch or 'default'}, repo={repo_dir.name}]"
            )

        # Verify remote branch was actually updated
        remote_branch = branch or "HEAD"
        _, ls_out = _run_git(["ls-remote", "--exit-code", "origin", remote_branch], cwd=repo_dir)
        _, local_hash = _run_git(["rev-parse", "HEAD"], cwd=repo_dir)

        if ls_out and local_hash and local_hash[:8] in ls_out:
            return (
                f"✅ Git Push VERIFIED (remote branch updated):\n{out}\n"
                f"[EVIDENCE: push returncode=0, remote_hash={local_hash[:12]}, "
                f"branch={remote_branch}, repo={repo_dir.name}, "
                f"remote_verified=True]"
            )
        else:
            return (
                f"⚠️ Git Push executed but remote verification inconclusive:\n{out}\n"
                f"[EVIDENCE: push returncode=0, branch={remote_branch}, "
                f"repo={repo_dir.name}, remote_verified=UNVERIFIED, "
                f"ls_remote_output='{ls_out[:200]}']"
            )

    elif action == "verify_remote":
        # Explicit remote verification step
        remote_branch = branch or "HEAD"
        code, ls_out = _run_git(["ls-remote", "--exit-code", "origin", remote_branch], cwd=repo_dir)
        _, local_hash = _run_git(["rev-parse", "HEAD"], cwd=repo_dir)
        if code == 0 and ls_out:
            return (
                f"✅ Remote branch '{remote_branch}' verified on GitHub:\n{ls_out[:400]}\n"
                f"[EVIDENCE: remote_verified=True, local_hash={local_hash[:12]}]"
            )
        return f"❌ Remote verification FAILED for branch '{remote_branch}' (returncode {code}):\n{ls_out}"

    return f"Unknown action '{action}'."
