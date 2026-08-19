# tools/web_tools.py — BR JARVIS High-Fidelity Web Capability Suite
"""
High-Fidelity Web Capability Suite for BR JARVIS MK40.2 / MK41.
Provides search, headless DOM text extraction, raw retrieval, and structured ToolResults.
"""

from __future__ import annotations

import json

from .domain import ToolErrorCode
from .registry import _run_async, register_tool
from .tool_result import ToolResult
from .web import fetch_page as core_fetch_page
from .web import fetch_raw as core_fetch_raw
from .web import web_search as core_web_search


@register_tool(
    name="web_search",
    description="Search the web using DuckDuckGo. Returns structured results with titles, URLs, and snippets. Args: 'query' (search string), 'max_results' (optional integer, default: 5).",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "Max results to return (default 5)"},
        },
        "required": ["query"],
    },
    category="web",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
    verification_strategy="NONE",
)
def tool_web_search(args: dict) -> ToolResult:
    """Execute structured web search."""
    query = str(args.get("query", "")).strip()
    if not query:
        return ToolResult.failed("web_search", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'query' is required.")

    max_results = int(args.get("max_results", 5))

    try:
        results = _run_async(core_web_search(query, max_results))
        evidence = f"Found {len(results)} search results for query '{query}'."
        return ToolResult.success(
            tool_name="web_search",
            data=results,
            output=json.dumps(results, indent=2, default=str),
            evidence=evidence,
            verified=True,
            metadata={"query": query, "count": len(results)},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="web_search",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Web search failed for '{query}': {e}",
        )


@register_tool(
    name="fetch_page",
    description="Fetch and extract readable text content from a web URL using a headless browser. Args: 'url' (web page URL to fetch).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Web URL to fetch"},
        },
        "required": ["url"],
    },
    category="web",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
    verification_strategy="NONE",
)
def tool_fetch_page(args: dict) -> ToolResult:
    """Fetch and extract readable text content from a URL."""
    url = str(args.get("url", "")).strip()
    if not url:
        return ToolResult.failed("fetch_page", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'url' is required.")

    try:
        text = _run_async(core_fetch_page(url))
        clean_text = (text or "")[:12000]
        evidence = f"Extracted {len(clean_text):,} characters from '{url}'."
        return ToolResult.success(
            tool_name="fetch_page",
            data={"url": url, "text": clean_text, "char_count": len(clean_text)},
            output=clean_text,
            evidence=evidence,
            verified=bool(clean_text.strip()),
            metadata={"url": url, "char_count": len(clean_text)},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="fetch_page",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error fetching page '{url}': {e}",
        )


@register_tool(
    name="fetch_raw",
    description="Fetch raw HTML or plain text from a URL via HTTP GET. Args: 'url' (target URL).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL"},
        },
        "required": ["url"],
    },
    category="web",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
    verification_strategy="NONE",
)
def tool_fetch_raw(args: dict) -> ToolResult:
    """Fetch raw HTTP response content."""
    url = str(args.get("url", "")).strip()
    if not url:
        return ToolResult.failed("fetch_raw", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'url' is required.")

    try:
        raw_text = _run_async(core_fetch_raw(url))
        clean_raw = (raw_text or "")[:12000]
        evidence = f"Retrieved {len(clean_raw):,} raw characters from '{url}'."
        return ToolResult.success(
            tool_name="fetch_raw",
            data={"url": url, "raw_content": clean_raw, "char_count": len(clean_raw)},
            output=clean_raw,
            evidence=evidence,
            verified=bool(clean_raw.strip()),
            metadata={"url": url, "char_count": len(clean_raw)},
        )
    except Exception as e:
        return ToolResult.failed(
            tool_name="fetch_raw",
            error_code=ToolErrorCode.EXECUTION_EXCEPTION,
            message=f"Error retrieving raw content from '{url}': {e}",
        )
