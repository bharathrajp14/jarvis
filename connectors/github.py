# connectors/github.py — GitHub Connector (Free PAT Token)
"""
GitHub connector for repositories, issues, pull requests, and code search.
Requires a free GitHub Personal Access Token (PAT):
  github.com → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
  Scopes: repo (read), issues (read) — takes 2 minutes
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from connectors.base import BaseConnector, ConnectorTool

logger = logging.getLogger("JARVIS.Connectors.GitHub")

_API = "https://api.github.com"


class GitHubConnector(BaseConnector):

    def __init__(self):
        self._token = os.environ.get("GITHUB_TOKEN", "").strip()

    @property
    def connector_id(self) -> str:
        return "github"

    @property
    def display_name(self) -> str:
        return "GitHub"

    @property
    def description(self) -> str:
        return "Search repos, read issues, pull requests, files, and code"

    @property
    def icon(self) -> str:
        return "🐙"

    @property
    def requires_auth(self) -> bool:
        return True

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    @property
    def auth_hint(self) -> str:
        return (
            "Add GITHUB_TOKEN=ghp_xxxx to your .env file.\n"
            "Get free token: github.com → Settings → Developer Settings → PAT (classic)\n"
            "Required scopes: repo (read)"
        )

    def list_tools(self) -> List[ConnectorTool]:
        return [
            ConnectorTool(
                name="search_repos",
                description="Search GitHub repositories by keyword",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (e.g. 'python AI assistant')"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="get_repo",
                description="Get details about a specific GitHub repository",
                parameters={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner username"},
                        "repo": {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="list_issues",
                description="List open issues in a GitHub repository",
                parameters={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["owner", "repo"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="get_file",
                description="Read the content of a file in a GitHub repository",
                parameters={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "path": {"type": "string", "description": "File path in repo (e.g. 'README.md')"},
                        "branch": {"type": "string", "default": "main"},
                    },
                    "required": ["owner", "repo", "path"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="search_code",
                description="Search code across GitHub repositories",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Code search query"},
                        "language": {"type": "string", "description": "Filter by language (e.g. 'python')"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
                requires_auth=True,
            ),
            ConnectorTool(
                name="list_prs",
                description="List pull requests in a GitHub repository",
                parameters={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "state": {"type": "string", "default": "open"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["owner", "repo"],
                },
                requires_auth=True,
            ),
        ]

    def _fetch(self, path: str, params: dict = None) -> Any:
        url = f"{_API}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "JARVIS-ConnectorHub/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=10.0) as r:
            return json.loads(r.read().decode())

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "search_repos":
            return self._search_repos(args.get("query", ""), int(args.get("limit", 5)))
        elif tool_name == "get_repo":
            return self._get_repo(args["owner"], args["repo"])
        elif tool_name == "list_issues":
            return self._list_issues(args["owner"], args["repo"], args.get("state", "open"), int(args.get("limit", 10)))
        elif tool_name == "get_file":
            return self._get_file(args["owner"], args["repo"], args["path"], args.get("branch", "main"))
        elif tool_name == "search_code":
            return self._search_code(args.get("query", ""), args.get("language", ""), int(args.get("limit", 5)))
        elif tool_name == "list_prs":
            return self._list_prs(args["owner"], args["repo"], args.get("state", "open"), int(args.get("limit", 10)))
        return f"Unknown tool: {tool_name}"

    def _search_repos(self, query: str, limit: int = 5) -> str:
        try:
            data = self._fetch("/search/repositories", {"q": query, "per_page": limit, "sort": "stars"})
            items = data.get("items", [])
            if not items:
                return f"No repositories found for '{query}'."
            lines = [f"🐙 **GitHub Repository Search: '{query}'**\n"]
            for repo in items:
                name = repo.get("full_name", "")
                desc = repo.get("description", "No description") or "No description"
                stars = repo.get("stargazers_count", 0)
                lang = repo.get("language", "")
                url = repo.get("html_url", "")
                lines.append(f"• **{name}** ⭐{stars:,} {f'[{lang}]' if lang else ''}\n  {desc[:120]}\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"GitHub search error: {e}"

    def _get_repo(self, owner: str, repo: str) -> str:
        try:
            r = self._fetch(f"/repos/{owner}/{repo}")
            return (
                f"🐙 **{r['full_name']}**\n"
                f"• Description: {r.get('description', 'N/A')}\n"
                f"• Language: {r.get('language', 'N/A')}\n"
                f"• Stars: {r.get('stargazers_count', 0):,} | Forks: {r.get('forks_count', 0):,}\n"
                f"• Open Issues: {r.get('open_issues_count', 0)}\n"
                f"• Default Branch: {r.get('default_branch', 'main')}\n"
                f"• License: {r.get('license', {}).get('name', 'None') if r.get('license') else 'None'}\n"
                f"• Last Updated: {r.get('updated_at', 'N/A')[:10]}\n"
                f"🔗 {r.get('html_url', '')}"
            )
        except Exception as e:
            return f"GitHub repo error: {e}"

    def _list_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> str:
        try:
            issues = self._fetch(f"/repos/{owner}/{repo}/issues", {"state": state, "per_page": limit})
            if not issues:
                return f"No {state} issues in {owner}/{repo}."
            lines = [f"🐙 **{owner}/{repo} — {state.title()} Issues**\n"]
            for issue in issues[:limit]:
                num = issue.get("number", "")
                title = issue.get("title", "")
                labels = ", ".join(l["name"] for l in issue.get("labels", []))
                url = issue.get("html_url", "")
                label_str = f" [{labels}]" if labels else ""
                lines.append(f"• #{num}: {title}{label_str}\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"GitHub issues error: {e}"

    def _get_file(self, owner: str, repo: str, path: str, branch: str = "main") -> str:
        try:
            import base64
            data = self._fetch(f"/repos/{owner}/{repo}/contents/{path}", {"ref": branch})
            if data.get("type") != "file":
                return f"'{path}' is not a file."
            content_b64 = data.get("content", "")
            content = base64.b64decode(content_b64).decode("utf-8", errors="replace")
            # Truncate large files
            if len(content) > 4000:
                content = content[:4000] + "\n\n[...File truncated at 4000 chars]"
            return f"📄 **{owner}/{repo}/{path}** (branch: {branch})\n\n```\n{content}\n```"
        except Exception as e:
            return f"GitHub file error: {e}"

    def _search_code(self, query: str, language: str = "", limit: int = 5) -> str:
        try:
            q = query
            if language:
                q += f" language:{language}"
            data = self._fetch("/search/code", {"q": q, "per_page": limit})
            items = data.get("items", [])
            if not items:
                return f"No code found for '{query}'."
            lines = [f"🐙 **GitHub Code Search: '{query}'**\n"]
            for item in items[:limit]:
                repo = item.get("repository", {}).get("full_name", "")
                path = item.get("path", "")
                url = item.get("html_url", "")
                lines.append(f"• {repo} / `{path}`\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"GitHub code search error: {e}"

    def _list_prs(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> str:
        try:
            prs = self._fetch(f"/repos/{owner}/{repo}/pulls", {"state": state, "per_page": limit})
            if not prs:
                return f"No {state} pull requests in {owner}/{repo}."
            lines = [f"🐙 **{owner}/{repo} — {state.title()} Pull Requests**\n"]
            for pr in prs[:limit]:
                num = pr.get("number", "")
                title = pr.get("title", "")
                user = pr.get("user", {}).get("login", "")
                url = pr.get("html_url", "")
                lines.append(f"• #{num}: {title} by @{user}\n  🔗 {url}")
            return "\n".join(lines)
        except Exception as e:
            return f"GitHub PRs error: {e}"

    def health_check(self) -> bool:
        try:
            self._fetch("/user")
            return True
        except Exception:
            return False
