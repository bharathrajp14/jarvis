# tools/qa_testing_tool.py — Autonomous Background Web QA & Testing Suite for BR JARVIS
"""
Autonomous Web QA & Software Testing Engine.
Allows JARVIS to run background browser tests, validate DOM assertions, record JS console/network traces,
and generate structured markdown test reports.
"""
from __future__ import annotations

import logging
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool, _run_async
from tools.browser_automation import (
    _get_or_create_page,
    get_browser_trace_logs,
    clear_browser_trace_logs,
    _PLAYWRIGHT_AVAILABLE,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


@register_tool(
    name="qa_run_browser_test",
    description="Run an autonomous background end-to-end browser test flow on a target URL or local dev server.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target website URL or local server (e.g. http://localhost:3000)"},
            "steps": {
                "type": "array",
                "description": "List of test step objects e.g. [{'action': 'click', 'selector': '#login'}, {'action': 'type', 'selector': '#user', 'value': 'admin'}, {'action': 'assert_text', 'text': 'Dashboard'}]",
                "items": {"type": "object"}
            },
            "headless": {"type": "boolean", "description": "Run in background without opening window (default true)"},
            "screenshot_name": {"type": "string", "description": "Filename for final test screenshot (default test_result.png)"}
        },
        "required": ["url"]
    }
)
def qa_run_browser_test(args: dict) -> str:
    """Execute an autonomous browser test flow."""
    url = args["url"].strip()
    steps = args.get("steps", [])
    headless = args.get("headless", True)
    screenshot_name = args.get("screenshot_name", "test_result.png").strip()

    if not _PLAYWRIGHT_AVAILABLE:
        return "❌ QA Engine Error: Playwright is not installed. Install with `pip install playwright && playwright install chromium`."

    clear_browser_trace_logs()
    results = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "step_results": [],
        "passed": True,
        "screenshot_path": None,
        "console_logs": [],
        "page_errors": []
    }

    async def _execute():
        page = await _get_or_create_page(headless=headless)
        start_t = time.time()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            results["step_results"].append({
                "step": 0,
                "action": "navigate",
                "target": url,
                "status": "PASS",
                "duration_ms": round((time.time() - start_t) * 1000, 2)
            })
        except Exception as e:
            results["step_results"].append({
                "step": 0,
                "action": "navigate",
                "target": url,
                "status": "FAIL",
                "error": str(e)
            })
            results["passed"] = False
            return json.dumps(results, indent=2)

        for i, step in enumerate(steps, start=1):
            act = step.get("action", "").lower().strip()
            sel = step.get("selector", "").strip()
            val = step.get("value", "")
            txt = step.get("text", "")
            step_t = time.time()

            try:
                if act == "click":
                    await page.click(sel, timeout=10000)
                    res = {"status": "PASS"}
                elif act in ("type", "fill"):
                    await page.fill(sel, str(val), timeout=10000)
                    res = {"status": "PASS"}
                elif act == "assert_text":
                    content = await page.content()
                    if txt in content:
                        res = {"status": "PASS", "found_text": txt}
                    else:
                        res = {"status": "FAIL", "error": f"Expected text '{txt}' not found on page"}
                        results["passed"] = False
                elif act == "assert_selector":
                    elem = await page.query_selector(sel)
                    if elem:
                        res = {"status": "PASS", "found_selector": sel}
                    else:
                        res = {"status": "FAIL", "error": f"Selector '{sel}' not found"}
                        results["passed"] = False
                elif act == "wait":
                    wait_ms = int(step.get("duration_ms", 1000))
                    await asyncio.sleep(wait_ms / 1000.0)
                    res = {"status": "PASS", "waited_ms": wait_ms}
                else:
                    res = {"status": "SKIP", "reason": f"Unknown action '{act}'"}

            except Exception as ex:
                res = {"status": "FAIL", "error": str(ex)}
                results["passed"] = False

            res["step"] = i
            res["action"] = act
            res["duration_ms"] = round((time.time() - step_t) * 1000, 2)
            results["step_results"].append(res)

        # Capture final visual screenshot
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ss_path = REPORTS_DIR / screenshot_name
        try:
            await page.screenshot(path=str(ss_path), full_page=True)
            results["screenshot_path"] = str(ss_path)
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
        trace = get_browser_trace_logs()
        results["console_logs"] = trace["console_logs"]
        results["page_errors"] = trace["page_errors"]

        return json.dumps(results, indent=2)

    try:
        return _run_async(_execute())
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, indent=2)


@register_tool(
    name="qa_assert_page_state",
    description="Assert background page conditions (URL match, text presence, selector existence, no console errors).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL to open and evaluate"},
            "url_contains": {"type": "string", "description": "Expected substring in final page URL"},
            "text_visible": {"type": "string", "description": "Expected visible text on page"},
            "selector_exists": {"type": "string", "description": "Expected CSS selector on page"},
            "timeout_ms": {"type": "integer", "description": "Navigation timeout in ms (default 15000)"},
            "fail_on_console_error": {"type": "boolean", "description": "Fail test if JS console errors detected (default false)"}
        },
        "required": ["url"]
    }
)
def qa_assert_page_state(args: dict) -> str:
    """Validate DOM assertions on a web page."""
    url = args["url"].strip()
    url_contains = args.get("url_contains")
    text_visible = args.get("text_visible")
    selector_exists = args.get("selector_exists")
    timeout_ms = int(args.get("timeout_ms", 15000))
    fail_on_console_error = args.get("fail_on_console_error", False)

    clear_browser_trace_logs()
    assertions = []
    overall_pass = True

    async def _assert():
        nonlocal overall_pass
        page = await _get_or_create_page(headless=True)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as net_err:
            return json.dumps({
                "url": url,
                "overall_pass": False,
                "error": f"Navigation failed or timed out ({timeout_ms}ms): {net_err}"
            }, indent=2)

        current_url = page.url
        if url_contains:
            passed = url_contains in current_url
            assertions.append({"assertion": f"url_contains('{url_contains}')", "passed": passed, "actual": current_url})
            if not passed: overall_pass = False

        if text_visible:
            content = await page.content()
            passed = text_visible in content
            assertions.append({"assertion": f"text_visible('{text_visible}')", "passed": passed})
            if not passed: overall_pass = False

        if selector_exists:
            elem = await page.query_selector(selector_exists)
            passed = elem is not None
            assertions.append({"assertion": f"selector_exists('{selector_exists}')", "passed": passed})
            if not passed: overall_pass = False

        trace = get_browser_trace_logs()
        if fail_on_console_error and trace["page_errors"]:
            assertions.append({"assertion": "no_console_errors", "passed": False, "errors": trace["page_errors"]})
            overall_pass = False

        return json.dumps({
            "url": current_url,
            "overall_pass": overall_pass,
            "assertions": assertions,
            "trace_summary": {
                "console_log_count": len(trace["console_logs"]),
                "page_error_count": len(trace["page_errors"])
            }
        }, indent=2)

    try:
        return _run_async(_assert())
    except Exception as e:
        return json.dumps({"overall_pass": False, "error": str(e)}, indent=2)


@register_tool(
    name="qa_generate_report",
    description="Generate a comprehensive Markdown QA Audit Report from test execution results.",
    parameters={
        "type": "object",
        "properties": {
            "test_name": {"type": "string", "description": "Title of the test suite or application"},
            "results_json": {"type": "string", "description": "JSON string or payload of test results"},
            "report_filename": {"type": "string", "description": "Filename for markdown report (default qa_report.md)"}
        },
        "required": ["test_name", "results_json"]
    }
)
def qa_generate_report(args: dict) -> str:
    """Generate Markdown QA report file."""
    test_name = args["test_name"].strip()
    raw_results = args["results_json"]
    filename = args.get("report_filename", f"qa_report_{int(time.time())}.md").strip()

    try:
        data = json.loads(raw_results) if isinstance(raw_results, str) else raw_results
    except Exception:
        data = {"raw": raw_results}

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORTS_DIR / filename

    status_badge = "✅ PASSED" if data.get("passed", data.get("overall_pass", True)) else "❌ FAILED"
    
    md_content = f"""# 🧪 QA Audit Report: {test_name}

**Status**: {status_badge}  
**Timestamp**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Target URL**: `{data.get('url', 'N/A')}`

---

## 📊 Summary
* **Passed**: `{data.get('passed', data.get('overall_pass', True))}`
* **Console Errors**: `{len(data.get('page_errors', []))}`
* **Console Logs**: `{len(data.get('console_logs', []))}`

---

## 📝 Step Execution Details
```json
{json.dumps(data.get('step_results', data.get('assertions', [])), indent=2)}
```

---

## 🐞 Console Logs & Page Errors
```text
{chr(10).join(data.get('page_errors', [])) or 'No uncaught page errors detected.'}
```

---

*Report automatically generated by BR JARVIS QA Engine.*
"""
    try:
        report_file.write_text(md_content, encoding="utf-8")
        return f"✅ QA Audit Report generated successfully at `{report_file}`"
    except Exception as e:
        return f"❌ Failed to write report file: {e}"
