# tools/web_tools.py — JARVIS MK37 Web Tools Plugin
"""
Web tools plugin for JARVIS MK37. Contains web_search, fetch_page, and fetch_raw.
"""
from __future__ import annotations

import json
from .registry import register_tool, _run_async
from .web import web_search as core_web_search, fetch_page as core_fetch_page, fetch_raw as core_fetch_raw


@register_tool(
    name="web_search",
    description="Search the web using DuckDuckGo. Returns a list of results with titles, URLs, and snippets.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "Max results to return (default 5)"},
        },
        "required": ["query"],
    }
)
def tool_web_search(args: dict) -> str:
    query = args["query"]
    max_results = args.get("max_results", 5)
    results = _run_async(core_web_search(query, max_results))
    return json.dumps(results, indent=2, default=str)


@register_tool(
    name="fetch_page",
    description="Fetch and extract text content from a URL using a headless browser.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        },
        "required": ["url"],
    }
)
def tool_fetch_page(args: dict) -> str:
    url = args["url"]
    text = _run_async(core_fetch_page(url))
    return text[:8000]


@register_tool(
    name="fetch_raw",
    description="Fetch raw HTML/text content from a URL via HTTP GET.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        },
        "required": ["url"],
    }
)
def tool_fetch_raw(args: dict) -> str:
    url = args["url"]
    text = _run_async(core_fetch_raw(url))
    return text[:8000]
