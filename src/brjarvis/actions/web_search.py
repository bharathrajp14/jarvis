#web_search.py
import logging
import sys
from pathlib import Path

from ._gemini_client import get_gemini_client, get_proxy_model

logger = logging.getLogger("JARVIS.Actions.WebSearch")

from brjarvis.core.paths import paths

def _get_base_dir() -> Path:
    return paths.PROJECT_ROOT


BASE_DIR = _get_base_dir()


def _gemini_search(query: str) -> str:
    client = get_gemini_client()
    model = get_proxy_model(proxy_alias="gemini-3.5-flash", real_model="gemini-2.5-flash")
    response = client.models.generate_content(
        model=model,
        contents=query,
    )

    text = ""
    if hasattr(response, "candidates") and response.candidates:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                text += part.text
    elif hasattr(response, "text") and response.text:
        text = response.text

    text = text.strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


def _tavily_search(query: str, max_results: int = 6) -> list[dict]:
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        try:
            data = json.loads((paths.CONFIG_ROOT / "api_keys.json").read_text(encoding="utf-8"))
            key = data.get("tavily_api_key", "").strip()
        except Exception:
            key = ""
    if not key:
        return []
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps({"api_key": key, "query": query, "max_results": max_results}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            out = []
            for r in data.get("results", []):
                out.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("content", ""),
                    "url":     r.get("url", ""),
                    "source":  "Tavily",
                })
            return out
    except Exception as e:
        logger.debug("[WebSearch] Tavily notice: %s", e)
        return []


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    # 1. High-speed primary: Tavily
    tav_results = _tavily_search(query, max_results=max_results)
    if tav_results:
        return tav_results

    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results = []
    try:
        with DDGS(timeout=5) as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("href",   ""),
                })
    except Exception as e:
        logger.debug("[WebSearch] DDG notice: %s", e)
    return results


def _ddg_news(query: str, max_results: int = 8) -> list[dict]:
    """DDG news search — returns actual articles, not website homepages."""
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                results.append({
                    "title":   r.get("title",  ""),
                    "snippet": r.get("body",   ""),
                    "url":     r.get("url",    ""),
                    "source":  r.get("source", ""),
                })
    except Exception as e:
        logger.warning("DDG news() failed (%s) — falling back to text search", e)
        results = _ddg_search(query, max_results=max_results)
    return results


def _format_ddg(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"):   lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"):     lines.append(f"   Source: {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_news(query: str, results: list[dict]) -> str:
    if not results:
        return f"No news found for: {query}"

    lines = [f"Latest news: {query}\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        if not title:
            continue
        src = f"  [{r['source']}]" if r.get("source") else ""
        lines.append(f"{i}. {title}{src}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:140]}")
        if r.get("url"):
            lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()


# ── Briefing helper ────────────────────────────────────────────────────────────

def _gemini_headlines(n: int = 5) -> tuple[list[str], str]:
    """
    Fetches current headlines via Gemini grounded search.
    Optimised for speed: minimal prompt + strict token cap.
    Returns (headline_list, raw_text_for_display).
    """
    import re

    client = get_gemini_client()
    model = get_proxy_model(proxy_alias="gemini-3.5-flash", real_model="gemini-2.5-flash")
    response = client.models.generate_content(
        model=model,
        contents=f"Current world news: {n} headlines. Numbered list, titles only.",
    )

    raw = ""
    if hasattr(response, "candidates") and response.candidates:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                raw += part.text
    elif hasattr(response, "text") and response.text:
        raw = response.text

    headlines = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Only accept lines that begin with a number — skips preamble/closing sentences
        if not re.match(r'^[\d]+[.\)\-]', line):
            continue
        clean = re.sub(r'^[\d]+[.\)\-]\s*', '', line)
        clean = re.sub(r'^\*+\s*',          '', clean).strip()
        if clean and len(clean) > 10:
            headlines.append(clean)

    return headlines[:n], raw.strip()


# ── Modes ──────────────────────────────────────────────────────────────────────

def _search(query: str) -> str:
    """Default search — Gemini grounded, DDG fallback."""
    try:
        return _gemini_search(query)
    except Exception as e:
        logger.warning("Gemini failed (%s) — trying DDG...", e)
        results = _ddg_search(query)
        return _format_ddg(query, results)


def _news(query: str) -> str:
    """
    Runs Gemini grounded search AND DDG news in parallel.
    Returns whichever delivers a valid result first; cancels the other.
    """
    import threading

    gemini_query = f"latest news today: {query}" if query else "top world news today"
    ddg_query    = query if query else "world news today"

    result_box  = [None]   # first valid result lands here
    lock        = threading.Lock()
    done_evt    = threading.Event()
    failures    = [0]

    def _store(r: str) -> None:
        if r and len(r) > 60:
            with lock:
                if result_box[0] is None:
                    result_box[0] = r
            done_evt.set()
        else:
            with lock:
                failures[0] += 1
                if failures[0] >= 2:   # both failed — unblock caller
                    done_evt.set()

    def _try_gemini():
        try:
            _store(_gemini_search(gemini_query))
        except Exception as e:
            logger.warning("Gemini news failed (%s)", e)
            _store("")

    def _try_ddg():
        try:
            results = _ddg_news(ddg_query, max_results=8)
            _store(_format_news(ddg_query, results))
        except Exception as e:
            logger.warning("DDG news failed (%s)", e)
            _store("")

    threading.Thread(target=_try_gemini, daemon=True).start()
    threading.Thread(target=_try_ddg,    daemon=True).start()

    done_evt.wait(timeout=10.0)
    return result_box[0] or f"No news found for: {query}"


def _research(query: str) -> str:
    """
    Deep dive — asks Gemini for a comprehensive answer with context.
    Falls back to a wider DDG fetch.
    """
    research_query = (
        f"Comprehensive, detailed explanation of: {query}. "
        "Include background context, key facts, current state, and important nuances."
    )
    try:
        return _gemini_search(research_query)
    except Exception as e:
        logger.warning("Research Gemini failed (%s) — DDG fallback...", e)
        results = _ddg_search(query, max_results=10)
        return _format_ddg(query, results)


def _price(query: str) -> str:
    """Product price lookup — searches for current market prices."""
    price_query = f"current price of {query} — how much does it cost today"
    try:
        return _gemini_search(price_query)
    except Exception as e:
        logger.warning("Price Gemini failed (%s) — DDG fallback...", e)
        results = _ddg_search(f"{query} price buy", max_results=6)
        return _format_ddg(query, results)


def _compare(items: list[str], aspect: str) -> str:
    query = (
        f"Compare {', '.join(items)} in terms of {aspect}. "
        "Give specific facts and data."
    )
    try:
        return _gemini_search(query)
    except Exception as e:
        logger.warning("Gemini compare failed: %s — falling back to DDG", e)

    all_results: dict[str, list] = {}
    for item in items:
        try:
            all_results[item] = _ddg_search(f"{item} {aspect}", max_results=3)
        except Exception:
            all_results[item] = []

    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        lines.append(f"\n▸ {item}")
        for r in all_results.get(item, [])[:2]:
            if r.get("snippet"):
                lines.append(f"  • {r['snippet']}")
            if r.get("url"):
                lines.append(f"    {r['url']}")
    return "\n".join(lines)


# ── Public entry point ─────────────────────────────────────────────────────────

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query  = params.get("query", "").strip()
    mode   = params.get("mode",  "search").lower().strip()
    items  = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query."

    if items and mode not in ("compare",):
        mode = "compare"

    if player:
        player.write_log(f"[Search:{mode}] {query or ', '.join(items)}")

    logger.info("mode=%r  query=%r", mode, query)

    try:
        if mode == "compare" and items:
            return _compare(items, aspect)
        if mode == "news":
            return _news(query)
        if mode == "research":
            return _research(query)
        if mode == "price":
            return _price(query)
        return _search(query)

    except Exception as e:
        logger.error("All backends failed: %s", e)
        return f"Search failed: {e}"
