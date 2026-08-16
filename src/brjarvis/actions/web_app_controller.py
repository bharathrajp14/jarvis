# actions/web_app_controller.py — JARVIS MK37 Web App Controller (Gmail & MS 365)
"""
High-level automated workflows for online web apps (Gmail & Microsoft 365).
"""
from __future__ import annotations

import asyncio
from typing import Any
from tools.browser_automation import _get_or_create_page, _run_async


async def gmail_compose_and_send_async(to: str, subject: str, body: str) -> str:
    """Navigate to Gmail, click Compose, fill in recipient/subject/body, and click Send."""
    try:
        page = await _get_or_create_page(headless=False)
        await page.goto("https://mail.google.com", wait_until="domcontentloaded", timeout=30000)

        # Wait for Compose button
        compose_btn = page.locator("text='Compose'").first
        await compose_btn.click(timeout=10000)
        await page.wait_for_timeout(1000)

        # Fill recipient 'To' field
        to_field = page.locator("input[aria-label='To recipients'], input[aria-label='To'], [name='to']").first
        await to_field.fill(to)
        await to_field.press("Enter")

        # Fill subject
        subj_field = page.locator("input[name='subjectbox'], input[aria-label='Subject']").first
        await subj_field.fill(subject)

        # Fill body message area
        body_field = page.locator("div[aria-label='Message Body'], div[role='textbox']").first
        await body_field.fill(body)
        await page.wait_for_timeout(500)

        # Click Send
        send_btn = page.locator("div[aria-label*='Send'], text='Send'").first
        await send_btn.click()
        await page.wait_for_timeout(1500)

        return f"⚡ Gmail Message Sent successfully to '{to}' with subject '{subject}'!"
    except Exception as e:
        return f"Gmail Send Error: {e}"


async def gmail_search_and_reply_async(query: str, reply_text: str) -> str:
    """Search Gmail inbox for a thread, open it, click Reply, and send reply."""
    try:
        page = await _get_or_create_page(headless=False)
        await page.goto("https://mail.google.com", wait_until="domcontentloaded", timeout=30000)

        # Fill search input
        search_box = page.locator("input[aria-label='Search mail'], input[name='q']").first
        await search_box.fill(query)
        await search_box.press("Enter")
        await page.wait_for_timeout(2000)

        # Open first thread result
        thread = page.locator("tr[role='row']").first
        await thread.click()
        await page.wait_for_timeout(1500)

        # Click Reply button
        reply_btn = page.locator("span[role='button']:has-text('Reply'), [aria-label*='Reply']").first
        await reply_btn.click()
        await page.wait_for_timeout(1000)

        # Fill reply box
        reply_box = page.locator("div[aria-label='Message Body'], div[role='textbox']").first
        await reply_box.fill(reply_text)

        # Click Send
        send_btn = page.locator("div[aria-label*='Send'], text='Send'").first
        await send_btn.click()
        await page.wait_for_timeout(1500)

        return f"⚡ Replied to Gmail thread matching query '{query}'!"
    except Exception as e:
        return f"Gmail Reply Error: {e}"


async def ms365_open_app_async(app: str = "home") -> str:
    """Open Microsoft 365 / Office Online application (Word, Excel, PowerPoint, Home)."""
    app_urls = {
        "home": "https://www.office.com",
        "word": "https://www.office.com/launch/word",
        "excel": "https://www.office.com/launch/excel",
        "powerpoint": "https://www.office.com/launch/powerpoint",
        "outlook": "https://outlook.office.com",
    }
    target_url = app_urls.get(app.lower().strip(), "https://www.office.com")
    try:
        page = await _get_or_create_page(headless=False)
        await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        return f"⚡ Opened Microsoft 365 '{app}' online ({title}) at {page.url}"
    except Exception as e:
        return f"MS 365 Open Error: {e}"
