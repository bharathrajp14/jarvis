# tools/browser_automation.py — JARVIS MK37 Interactive Browser Engine
"""
Playwright-driven interactive browser controller with session persistence for Gmail,
Microsoft 365, Outlook, and general web applications.
"""
from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional


from .registry import register_tool, _run_async

_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, BrowserContext, Page, ElementHandle  # type: ignore[import-not-found]
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

import logging
from brjarvis.core.paths import paths

logger = logging.getLogger("JARVIS.Tools.BrowserAutomation")

_USER_DATA_DIR = paths.WORKSPACE_ROOT / "browser_user_data"
_active_browser_context: Optional[Any] = None
_active_page: Optional[Any] = None
_playwright_instance: Optional[Any] = None
_last_page_console_logs: list[str] = []
_last_page_errors: list[str] = []
# Thread-safe lock protecting all browser global state mutations
_BROWSER_LOCK = threading.Lock()



def get_browser_trace_logs() -> dict:
    """Return accumulated browser console logs and page errors."""
    return {
        "console_logs": list(_last_page_console_logs),
        "page_errors": list(_last_page_errors)
    }


def clear_browser_trace_logs():
    """Clear accumulated trace logs."""
    _last_page_console_logs.clear()
    _last_page_errors.clear()


def _attach_trace_listeners(page: Any):
    """Attach console and error listeners to Playwright page."""
    try:
        page.on("console", lambda msg: _last_page_console_logs.append(f"[{msg.type.upper()}] {msg.text}") if len(_last_page_console_logs) < 200 else None)
        page.on("pageerror", lambda err: _last_page_errors.append(str(err)) if len(_last_page_errors) < 50 else None)
    except Exception:
        pass


async def _get_or_create_page(headless: bool = False) -> Page:
    """Ensure a persistent browser context and active page exist.

    BUG-8 FIX: The original code held _BROWSER_LOCK (a threading.Lock) across
    async await calls. threading.Lock is NOT async-aware and cannot be released
    during suspension — this caused a permanent deadlock when two concurrent tool
    calls both tried to get the browser page. Fix: only use the lock for the
    fast-path check and the state mutation; do all async work outside the lock.
    """
    global _active_browser_context, _active_page, _playwright_instance

    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright is not installed. Install with: pip install playwright && playwright install chromium")

    # Fast-path: page already exists and is open — no lock needed for read
    if _active_page and not _active_page.is_closed():
        return _active_page

    _USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Clean stale Chromium lock files that block re-launch after crash
    _lock_file = _USER_DATA_DIR / "SingletonLock"
    if _lock_file.exists():
        try:
            _lock_file.unlink()
        except OSError:
            pass

    # Do async work OUTSIDE the threading lock to avoid holding it across await
    playwright_inst = None
    browser_ctx = None

    with _BROWSER_LOCK:
        # Re-check inside lock (another thread may have created it)
        if _active_page and not _active_page.is_closed():
            return _active_page
        playwright_inst = _playwright_instance
        browser_ctx = _active_browser_context

    # Perform async Playwright initialization outside the threading lock
    if not playwright_inst:
        playwright_inst = await async_playwright().start()

    if not browser_ctx:
        browser_ctx = await playwright_inst.chromium.launch_persistent_context(
            user_data_dir=str(_USER_DATA_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )

    pages = browser_ctx.pages
    new_page = pages[0] if pages else await browser_ctx.new_page()
    _attach_trace_listeners(new_page)

    # Now update shared state under the lock
    with _BROWSER_LOCK:
        _playwright_instance = playwright_inst
        _active_browser_context = browser_ctx
        _active_page = new_page

    return new_page


async def _close_browser():
    """Cleanly close active browser instance."""
    global _active_browser_context, _active_page, _playwright_instance
    try:
        if _active_browser_context:
            await _active_browser_context.close()
        if _playwright_instance:
            await _playwright_instance.stop()
    except Exception:
        pass
    finally:
        _active_browser_context = None
        _active_page = None
        _playwright_instance = None


@register_tool(
    name="browser_open_url",
    description="Open a website in the interactive browser (e.g. Gmail, Microsoft 365, Outlook, or verified host HTML reports). Reuses logged-in sessions. Args: 'url' (required target URL or path), 'headless' (optional boolean).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL or host artifact path to open (e.g. https://mail.google.com or C:/Users/.../report.html)"},
            "headless": {"type": "boolean", "description": "Run in background without opening window (default false)"}
        },
        "required": ["url"]
    },
    category="browser",
    risk_level="low",
    permission_required="PUBLIC_READ",
    is_read_only=True,
    verification_strategy="BROWSER_DOM",
)
def browser_open_url(args: dict) -> Any:
    """Open a URL or verified host artifact in the persistent browser and return canonical ToolResult."""
    from brjarvis.agent.artifacts import get_artifact_manager
    from brjarvis.tools.tool_result import ToolResult
    from brjarvis.tools.domain import ToolErrorCode
    mgr = get_artifact_manager()

    if isinstance(args, str):
        raw_url = args.strip()
        headless = False
    else:
        raw_url = str(args.get("url") or args.get("uri") or args.get("link") or args.get("target") or args.get("path") or "").strip()
        headless = args.get("headless", False)

    if not raw_url:
        return ToolResult.failed("browser_open_url", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'url' is required.")

    # Sandbox / Host Artifact Interception Gateway
    success, resolved_target, rec = mgr.ensure_host_artifact(raw_url)
    if not success:
        logger.warning("Browser open handoff rejected: %s", resolved_target)
        mgr.record_browser_result(raw_url, opened=False, observed=False, browser_verified=False, error=resolved_target)
        return ToolResult.failed("browser_open_url", ToolErrorCode.PERMISSION_DENIED, f"Browser open rejected: {resolved_target}")

    # Convert local host paths to file:// URI for browser navigation
    if not (resolved_target.startswith("http://") or resolved_target.startswith("https://") or resolved_target.startswith("about:")):
        host_p = Path(resolved_target).resolve()
        nav_url = host_p.as_uri()
    else:
        nav_url = resolved_target

    async def _open():
        page = await _get_or_create_page(headless=headless)
        try:
            resp = await page.goto(nav_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as nav_err:
            mgr.record_browser_result(resolved_target, opened=True, observed=True, browser_verified=False, error=str(nav_err))
            return ToolResult.failed("browser_open_url", ToolErrorCode.EXECUTION_EXCEPTION, f"Could not navigate to '{nav_url}': {nav_err}")

        title = await page.title()
        content = ""
        try:
            content = (await page.content()).lower()
        except Exception:
            pass

        err_indicators = [
            "err_file_not_found",
            "file not found",
            "it may have been moved, edited, or deleted",
            "err_access_denied",
            "access denied"
        ]

        for ind in err_indicators:
            if ind in content or ind in title.lower():
                mgr.record_browser_result(resolved_target, opened=True, observed=True, browser_verified=False, error=f"Browser error indicator '{ind}' detected.")
                return ToolResult.failed("browser_open_url", ToolErrorCode.VERIFICATION_FAILED, f"Browser error screen: '{ind}'")

        # Verification succeeded
        mgr.record_browser_result(resolved_target, opened=True, observed=True, browser_verified=True)
        evidence = f"Opened '{title}' at {page.url} (Host target: {resolved_target})"
        return ToolResult.success(
            tool_name="browser_open_url",
            data={"url": page.url, "title": title, "target": resolved_target},
            output=f"⚡ {evidence}",
            evidence=evidence,
            verified=True,
            metadata={"url": page.url, "title": title},
        )

    try:
        return _run_async(_open())
    except Exception as e:
        mgr.record_browser_result(resolved_target, opened=False, observed=False, browser_verified=False, error=str(e))
        return ToolResult.failed("browser_open_url", ToolErrorCode.EXECUTION_EXCEPTION, f"Browser open error: {e}")


@register_tool(
    name="browser_click",
    description="Click a button, link, tab, or element on the current web page by visible text, ARIA label, or CSS selector.",
    parameters={
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Text, button label, or CSS selector to click (e.g., 'Compose', 'Send', 'Reply', '#btn')"}
        },
        "required": ["target"]
    },
    category="browser",
    risk_level="medium",
    permission_required="LOCAL_SYSTEM",
    is_read_only=False,
    verification_strategy="BROWSER_DOM",
)
def browser_click(args: dict) -> Any:
    """Click an element on the current browser page."""
    from brjarvis.tools.tool_result import ToolResult
    from brjarvis.tools.domain import ToolErrorCode

    if isinstance(args, str):
        target = args.strip()
    else:
        target = str(args.get("target") or args.get("selector") or args.get("element") or args.get("text") or "").strip()

    if not target:
        return ToolResult.failed("browser_click", ToolErrorCode.INVALID_ARGUMENT, "Parameter 'target' is required.")

    async def _click():
        page = await _get_or_create_page()
        selectors = [
            f"text='{target}'",
            f"text={target}",
            f"button:has-text('{target}')",
            f"a:has-text('{target}')",
            f"[aria-label='{target}']",
            target
        ]

        clicked = False
        last_err = None
        for sel in selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=1500):
                    await elem.click()
                    clicked = True
                    break
            except Exception as exc:
                last_err = exc

        if clicked:
            await page.wait_for_timeout(800)
            evidence = f"Clicked '{target}' on page {page.url}"
            return ToolResult.success(
                tool_name="browser_click",
                data={"clicked": target, "url": page.url},
                output=f"⚡ {evidence}",
                evidence=evidence,
                verified=True,
            )
        else:
            return ToolResult.failed(
                tool_name="browser_click",
                error_code=ToolErrorCode.VERIFICATION_FAILED,
                message=f"Could not find clickable element for '{target}' (Error: {last_err})",
            )

    try:
        return _run_async(_click())
    except Exception as e:
        return ToolResult.failed("browser_click", ToolErrorCode.EXECUTION_EXCEPTION, f"Browser click error: {e}")



@register_tool(
    name="browser_type",
    description="Type text into an input field or contenteditable area on the active web page.",
    parameters={
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Field text label, placeholder, name, or selector (e.g. 'To', 'Subject', 'Message body')"},
            "text": {"type": "string", "description": "Text content to type"},
            "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing"}
        },
        "required": ["target", "text"]
    }
)
def browser_type(args: dict) -> str:
    """Type text into a web page input element."""
    if isinstance(args, str):
        target = "input"
        text = args.strip()
        press_enter = False
    else:
        target = str(args.get("target") or args.get("selector") or args.get("element") or args.get("field") or "").strip()
        text = str(args.get("text") or args.get("content") or args.get("value") or "")
        press_enter = args.get("press_enter", False)

    if not target and not text:
        return "Type Error: 'target' and 'text' parameters are required."

    async def _type():
        page = await _get_or_create_page()
        selectors = [
            f"input[placeholder='{target}']",
            f"textarea[placeholder='{target}']",
            f"[aria-label='{target}']",
            f"input[name='{target}']",
            f"text={target}",
            target
        ]

        typed = False
        for sel in selectors:
            try:
                elem = page.locator(sel).first
                if await elem.is_visible(timeout=2000):
                    await elem.fill(text)
                    if press_enter:
                        await elem.press("Enter")
                    typed = True
                    break
            except Exception:
                pass

        if not typed:
            # Fallback: type directly into active focused element
            try:
                await page.keyboard.type(text)
                if press_enter:
                    await page.keyboard.press("Enter")
                typed = True
            except Exception:
                pass

        if typed:
            return f"⚡ Typed into '{target}' successfully."
        else:
            return f"Type Error: Could not locate input target '{target}'."

    try:
        return _run_async(_type())
    except Exception as e:
        return f"Browser Type Error: {e}"


@register_tool(
    name="browser_read_page",
    description="Read visible text and interactive form fields from the current web page.",
    parameters={"type": "object", "properties": {}}
)
def browser_read_page(args: dict) -> str:
    """Read inner text from current page."""
    async def _read():
        page = await _get_or_create_page()
        title = await page.title()
        body_text = await page.inner_text("body")
        return f"URL: {page.url}\nTitle: {title}\n\n--- Page Text ---\n{body_text[:5000]}"

    try:
        return _run_async(_read())
    except Exception as e:
        return f"Browser Read Error: {e}"


@register_tool(
    name="browser_new_tab",
    description="Open a new browser tab with an optional URL.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to open in the new tab (default 'about:blank')"}
        }
    }
)
def browser_new_tab(args: dict) -> str:
    """Open a new browser tab."""
    url = args.get("url", "about:blank").strip()

    async def _new_tab():
        global _active_page, _active_browser_context
        page = await _get_or_create_page()
        new_page = await _active_browser_context.new_page()
        if url and url != "about:blank":
            await new_page.goto(url, wait_until="domcontentloaded", timeout=30000)
        _active_page = new_page
        count = len(_active_browser_context.pages)
        return f"⚡ Opened new browser tab (Tab {count}). URL: {new_page.url}"

    try:
        return _run_async(_new_tab())
    except Exception as e:
        return f"Browser New Tab Error: {e}"


@register_tool(
    name="browser_switch_tab",
    description="Switch active browser focus to a specific tab by 0-based index.",
    parameters={
        "type": "object",
        "properties": {
            "index": {"type": "integer", "description": "0-based tab index to bring to focus"}
        },
        "required": ["index"]
    }
)
def browser_switch_tab(args: dict) -> str:
    """Switch active tab focus."""
    idx = args.get("index", 0)

    async def _switch():
        global _active_page, _active_browser_context
        page = await _get_or_create_page()
        pages = _active_browser_context.pages
        if 0 <= idx < len(pages):
            _active_page = pages[idx]
            await _active_page.bring_to_front()
            title = await _active_page.title()
            return f"⚡ Switched focus to Tab {idx} ('{title}')."
        else:
            return f"Switch Tab Error: Index {idx} out of range (Total open tabs: {len(pages)})."

    try:
        return _run_async(_switch())
    except Exception as e:
        return f"Browser Switch Tab Error: {e}"


@register_tool(
    name="browser_scroll",
    description="Scroll the active web page up or down, or scroll to top/bottom.",
    parameters={
        "type": "object",
        "properties": {
            "direction": {"type": "string", "description": "Scroll direction: 'down', 'up', 'top', or 'bottom'"},
            "amount": {"type": "integer", "description": "Pixel amount to scroll (default 500)"}
        }
    }
)
def browser_scroll(args: dict) -> str:
    """Scroll the current browser page."""
    direction = args.get("direction", "down").lower().strip()
    amount = args.get("amount", 500)

    async def _scroll():
        page = await _get_or_create_page()
        if direction == "down":
            await page.evaluate(f"window.scrollBy(0, {amount});")
        elif direction == "up":
            await page.evaluate(f"window.scrollBy(0, -{amount});")
        elif direction == "top":
            await page.evaluate("window.scrollTo(0, 0);")
        elif direction == "bottom":
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        return f"⚡ Scrolled page {direction}."

    try:
        return _run_async(_scroll())
    except Exception as e:
        return f"Browser Scroll Error: {e}"


@register_tool(
    name="browser_eval_js",
    description="Evaluate a custom JavaScript snippet inside the active web page context and return the result.",
    parameters={
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "JavaScript code string to evaluate (e.g. 'document.title' or 'document.links.length')"}
        },
        "required": ["script"]
    }
)
def browser_eval_js(args: dict) -> str:
    """Evaluate JavaScript inside the active page."""
    # FIXED: Use .get() to avoid KeyError if LLM omits the 'script' key
    script = (args.get("script") or args.get("code") or args.get("js") or "").strip()
    if not script:
        return "Browser JS Error: 'script' parameter is required."

    async def _eval():
        page = await _get_or_create_page()
        res = await page.evaluate(script)
        return f"⚡ JS Execution Result:\n{res}"

    try:
        return _run_async(_eval())
    except Exception as exc:
        return f"Browser JS Evaluation Error: {exc}"



@register_tool(
    name="browser_history",
    description="Execute browser history actions: 'back', 'forward', or 'reload'.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "Action name: 'back', 'forward', or 'reload'"}
        },
        "required": ["action"]
    }
)
def browser_history(args: dict) -> str:
    """Execute browser history action."""
    action = args["action"].lower().strip()

    async def _history():
        page = await _get_or_create_page()
        if action == "back":
            await page.go_back()
        elif action == "forward":
            await page.go_forward()
        elif action == "reload":
            await page.reload()
        return f"⚡ Executed browser history action '{action}' on {page.url}"

    try:
        return _run_async(_history())
    except Exception as e:
        return f"Browser History Error: {e}"


@register_tool(
    name="browser_screenshot",
    description="Capture a screenshot of the active browser web page and save it to workspace.",
    parameters={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Target PNG filename, default is browser_screenshot.png"}
        }
    }
)
def browser_screenshot(args: dict) -> str:
    """Capture page screenshot."""
    filename = args.get("filename", "browser_screenshot.png").strip()

    async def _screenshot():
        page = await _get_or_create_page()
        out_dir = paths.WORKSPACE_ROOT
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / filename
        await page.screenshot(path=str(out_path), full_page=False)
        return f"⚡ Captured browser screenshot: '{out_path}'"

    try:
        return _run_async(_screenshot())
    except Exception as e:
        return f"Browser Screenshot Error: {e}"
