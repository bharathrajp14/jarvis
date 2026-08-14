# tools/web.py — Upgraded Robust Multi-Engine Web Search & Scraping System
"""
Universal high-resilience web search & page extractor for BR-JARVIS.
Combines DuckDuckGo, Wikipedia API, Gemini Search Grounding, and HTTP/Playwright scrapers.
"""
from __future__ import annotations

import logging
import asyncio
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

_DDG_AVAILABLE = False
try:
    from ddgs import DDGS
    _DDG_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        _DDG_AVAILABLE = True
    except ImportError:
        _DDG_AVAILABLE = False

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception:
    _PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    """Clean HTML tags and normalize whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


async def search_wikipedia(query: str, max_results: int = 3) -> list[dict]:
    """Search Wikipedia API for factual summaries."""
    results = []
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit={max_results}&namespace=0&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "BR-JARVIS/37.5 (AI Assistant)"})
        loop = asyncio.get_running_loop()

        def _fetch():
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))

        data = await loop.run_in_executor(None, _fetch)
        if len(data) >= 4 and data[1]:
            titles, snippets, urls = data[1], data[2], data[3]
            for t, s, u in zip(titles, snippets, urls):
                results.append({
                    "title": f"Wikipedia: {t}",
                    "href": u,
                    "body": s or f"Wikipedia article for {t}.",
                    "source": "Wikipedia"
                })
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
    return results


async def search_duckduckgo(query: str, max_results: int = 8) -> list[dict]:
    """Perform search via DuckDuckGo."""
    if not _DDG_AVAILABLE:
        return []
    loop = asyncio.get_running_loop()

    def _do_ddg():
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            logger.warning(f"[WebSearch] DDG error: {e}")
            return []

    results = await loop.run_in_executor(None, _do_ddg)
    for r in results:
        r["source"] = "DuckDuckGo"
        r["title"] = _clean_text(r.get("title", ""))
        r["body"] = _clean_text(r.get("body", ""))
    return results


async def web_search(query: str, max_results: int = 8) -> list[dict]:
    """
    Multi-engine resilient web search.
    Tries DuckDuckGo -> Wikipedia -> Gemini Grounding fallback chain.
    """
    clean_query = query.strip()
    if not clean_query:
        return [{"error": "Empty search query provided."}]

    # 1. Primary: DuckDuckGo
    results = await search_duckduckgo(clean_query, max_results=max_results)

    # 2. Secondary: Wikipedia fallback/supplement
    if len(results) < 3:
        wiki_results = await search_wikipedia(clean_query, max_results=3)
        existing_urls = {r.get("href") for r in results}
        for wr in wiki_results:
            if wr["href"] not in existing_urls:
                results.append(wr)

    # 3. Tertiary: Gemini Grounded Search Fallback if zero results
    if not results:
        try:
            from backends.gemini import GeminiBackend
            gemini = GeminiBackend()
            if gemini.available:
                g_res = gemini.complete_with_search(
                    query=clean_query,
                    system="Provide a concise factual search summary with key details and sources."
                )
                if g_res and not g_res.startswith("ERROR"):
                    results.append({
                        "title": f"Gemini Grounded Search Result: {clean_query}",
                        "href": "https://google.com/search?q=" + urllib.parse.quote(clean_query),
                        "body": g_res[:1000],
                        "source": "Google Search Grounding"
                    })
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    if not results:
        return [{"error": f"No web search results found for: '{clean_query}'"}]

    return results[:max_results]


async def fetch_page(url: str) -> str:
    """Fetch rendered HTML page text content."""
    if _PLAYWRIGHT_AVAILABLE:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto(url, timeout=15000)
                text = await page.inner_text("body")
                await browser.close()
                return _clean_text(text[:10000])
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    return await fetch_raw(url)


async def fetch_raw(url: str) -> str:
    """Fetch raw text/HTML content from URL."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    if _HTTPX_AVAILABLE:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                return _clean_text(resp.text[:10000])
        except Exception as e:
            return f"HTTP error fetching URL: {e}"

    try:
        req = urllib.request.Request(url, headers=headers)
        loop = asyncio.get_running_loop()

        def _fetch_url():
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8", errors="replace")

        raw_text = await loop.run_in_executor(None, _fetch_url)
        return _clean_text(raw_text[:10000])
    except Exception as e:
        return f"Fetch error: {e}"
