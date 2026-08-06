# tools/autonomous_browser_agent.py — Autonomous Background Web Task Execution Subsystem
"""
Autonomous Web Task Agent for BR JARVIS.
Controls a background Playwright browser to execute end-to-end user-assigned web tasks
such as searching, extracting data, navigating multi-step workflows, and auto-filling forms.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from tools.registry import register_tool, _run_async
from tools.browser_automation import (
    _get_or_create_page,
    _PLAYWRIGHT_AVAILABLE,
)

logger = logging.getLogger("JARVIS.AutonomousWebAgent")


@register_tool(
    name="browser_execute_web_task",
    description="Autonomously execute a multi-step web task in a background browser (e.g. search, navigate, extract information, summarize).",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "High-level goal statement e.g. 'Search for Python 3.14 release features and extract key points'"},
            "start_url": {"type": "string", "description": "Starting URL (default: https://www.google.com)"},
            "max_steps": {"type": "integer", "description": "Maximum navigation steps to execute (default 5)"},
            "headless": {"type": "boolean", "description": "Run in background without opening browser window (default true)"}
        },
        "required": ["goal"]
    }
)
def browser_execute_web_task(args: dict) -> str:
    """Autonomously perform a web task in the background browser."""
    goal = args["goal"].strip()
    start_url = args.get("start_url", "https://www.google.com").strip()
    max_steps = args.get("max_steps", 5)
    headless = args.get("headless", True)

    if not _PLAYWRIGHT_AVAILABLE:
        return "❌ Autonomous Web Agent Error: Playwright is not installed. Install with `pip install playwright && playwright install chromium`."

    async def _run():
        page = await _get_or_create_page(headless=headless)
        
        # Step 1: Navigate to initial target or search engine
        if "http://" not in start_url and "https://" not in start_url:
            target_url = f"https://www.google.com/search?q={start_url}"
        else:
            target_url = start_url

        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            return f"❌ Web Task Error: Unable to open starting URL '{target_url}' — {e}"

        # Step 2: Handle search query if goal specifies search on Google/Bing
        if "google.com" in page.url or "bing.com" in page.url:
            search_terms = goal.lower().replace("search for", "").replace("find", "").strip()
            try:
                # Try finding search input box
                search_input = await page.query_selector("textarea[name='q'], input[name='q'], input[name='p']")
                if search_input:
                    await search_input.fill(search_terms)
                    await search_input.press("Enter")
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        # Step 3: Extract main text content from final page state
        extracted_text = await page.evaluate("""
            () => {
                // Remove non-content elements
                const selectors = ['script', 'style', 'nav', 'footer', 'header', 'iframe', '.ads', '#ads'];
                selectors.forEach(sel => document.querySelectorAll(sel).forEach(el => el.remove()));
                
                const body = document.querySelector('main') || document.querySelector('article') || document.body;
                return body ? body.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 20).join('\\n') : '';
            }
        """)

        # Truncate extracted text to top 1500 chars for clean LLM consumption
        lines = extracted_text.split("\n")[:30]
        cleaned_summary = "\n".join(lines)

        return json.dumps({
            "status": "success",
            "goal": goal,
            "final_url": page.url,
            "title": await page.title(),
            "extracted_content": cleaned_summary or "No main text content extracted.",
            "message": f"Successfully completed web task for goal: '{goal}'"
        }, indent=2)

    try:
        return _run_async(_run())
    except Exception as e:
        return f"❌ Autonomous Web Agent Task Failed: {e}"


@register_tool(
    name="browser_auto_navigate_and_extract",
    description="Navigate to any URL in background browser, clean page clutter, and extract main structured content.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target website URL"},
            "max_lines": {"type": "integer", "description": "Max text lines to return (default 40)"},
            "headless": {"type": "boolean", "description": "Run in background without opening window (default true)"}
        },
        "required": ["url"]
    }
)
def browser_auto_navigate_and_extract(args: dict) -> str:
    """Navigate to a website and extract clean article/body content."""
    url = args["url"].strip()
    max_lines = args.get("max_lines", 40)
    headless = args.get("headless", True)

    if not _PLAYWRIGHT_AVAILABLE:
        return "❌ Playwright not installed."

    async def _navigate():
        page = await _get_or_create_page(headless=headless)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        
        title = await page.title()
        text = await page.evaluate("""
            () => {
                const el = document.querySelector('main') || document.querySelector('article') || document.body;
                return el ? el.innerText : '';
            }
        """)
        
        filtered = [line.strip() for line in text.split("\n") if len(line.strip()) > 15][:max_lines]
        return json.dumps({
            "url": page.url,
            "title": title,
            "content": "\n".join(filtered)
        }, indent=2)

    try:
        return _run_async(_navigate())
    except Exception as e:
        return f"❌ Error navigating to {url}: {e}"


@register_tool(
    name="browser_fill_and_submit_form",
    description="Automatically fill out input fields on the active browser page and submit the form.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL of the page containing the form (optional if page is already open)"},
            "form_fields": {
                "type": "object",
                "description": "Dictionary of field selectors/names/placeholders to values e.g. {'username': 'john', 'email': 'john@example.com'}"
            },
            "submit_button": {"type": "string", "description": "CSS selector or button text to click for submission (optional)"}
        },
        "required": ["form_fields"]
    }
)
def browser_fill_and_submit_form(args: dict) -> str:
    """Auto-fill and submit form fields in background browser."""
    url = args.get("url", "").strip()
    fields = args["form_fields"]
    submit_button = args.get("submit_button", "").strip()

    if not _PLAYWRIGHT_AVAILABLE:
        return "❌ Playwright not installed."

    async def _fill():
        page = await _get_or_create_page(headless=True)
        if url:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)

        filled_count = 0
        for field_key, field_val in fields.items():
            # Try selector heuristics: #id, [name=key], [placeholder=key], [aria-label=key]
            selectors = [
                field_key,
                f"#{field_key}",
                f"[name='{field_key}']",
                f"[placeholder*='{field_key}']",
                f"[aria-label*='{field_key}']"
            ]
            for sel in selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem:
                        await elem.fill(str(field_val))
                        filled_count += 1
                        break
                except Exception:
                    continue

        # Handle form submission if button specified
        if submit_button:
            try:
                btn = await page.query_selector(submit_button) or await page.query_selector(f"button:has-text('{submit_button}'), input[type='submit']")
                if btn:
                    await btn.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception as e:
                if 'logger' in globals() or 'logger' in locals():
                    logger.debug('Suppressed exception: %s', e)
                else:
                    import logging
                    logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        return json.dumps({
            "status": "success",
            "fields_filled": filled_count,
            "current_url": page.url,
            "page_title": await page.title()
        }, indent=2)

    try:
        return _run_async(_fill())
    except Exception as e:
        return f"❌ Form submission error: {e}"
