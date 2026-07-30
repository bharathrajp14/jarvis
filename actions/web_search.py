# actions/web_search.py — Upgraded Web Search Action Module
"""
High-resilience Web Search powered by Multi-Engine Search Architecture.
Integrates DuckDuckGo, Wikipedia API, and Gemini Search Grounding with structured Markdown outputs.
"""
from __future__ import annotations

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.web import web_search as core_web_search, fetch_page as core_fetch_page


def _get_gemini():
    try:
        from backends.gemini import GeminiBackend
        return GeminiBackend()
    except Exception:
        return None


def _gemini_search(query: str) -> str:
    """Use Gemini's Google Search grounding for real-time web results."""
    gemini = _get_gemini()
    if gemini and gemini.available:
        try:
            return gemini.complete_with_search(
                query=query,
                system="You are a helpful research assistant. Provide accurate, up-to-date information with source citations when available. Be concise and factual."
            )
        except Exception as e:
            print(f"[WebSearch] Gemini grounding error: {e}")

    # Fallback to multi-engine search
    return _multi_engine_search_fmt(query)


def _multi_engine_search_fmt(query: str, max_results: int = 6) -> str:
    """Multi-engine search formatter."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(core_web_search(query, max_results=max_results))
        loop.close()

        if not results or "error" in results[0]:
            err = results[0].get("error") if results else "No results found"
            return f"Search notice: {err} for query '{query}'"

        lines = [f"🌐 Web Search Results for: '{query}'\n"]
        for i, r in enumerate(results, 1):
            source = r.get("source", "Web")
            title = r.get("title", "No Title")
            snippet = r.get("body", "No snippet available")
            url = r.get("href", "#")
            lines.append(f"### {i}. [{title}]({url}) `[{source}]`")
            lines.append(f"{snippet[:300]}\n")

        return "\n".join(lines).strip()

    except Exception as e:
        return f"Search unavailable: {e}. Query was: {query}"


def _compare(items: list[str], aspect: str) -> str:
    """Compare multiple items using Gemini or multi-engine search."""
    query = f"Compare {', '.join(items)} in terms of {aspect}. Be specific with data and facts."
    return _gemini_search(query)


def web_search(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query = params.get("query", "").strip()
    mode = params.get("mode", "search").lower().strip()
    items = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query."

    if items and mode != "compare":
        mode = "compare"

    if player and hasattr(player, "write_log"):
        player.write_log(f"[Search] {query or ', '.join(items)}")

    print(f"[WebSearch] 🔍 '{query or items}' mode={mode}")

    try:
        if mode == "compare" and items:
            return _compare(items, aspect)
        return _multi_engine_search_fmt(query)
    except Exception as e:
        return f"Search error: {e}"
