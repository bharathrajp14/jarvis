# redteam/report.py — Security Audit Report Generator
from __future__ import annotations

import html
from datetime import datetime

REPORT_TEMPLATE = """
# Penetration Test Report

**Client:** {client}
**Engagement ID:** {engagement_id}
**Date:** {date}
**Prepared by:** JARVIS MK37 / {operator}

---

## Executive Summary

{executive_summary}

---

## Scope

**In-scope targets:**
{scope_targets}

---

## Findings

{findings}

---

## Remediation Recommendations

{recommendations}

---

## Appendix: Tool Output

{appendix}
"""


def generate_report(data: dict) -> str:
    """Generate Markdown penetration test report."""
    findings_md = ""
    for i, f in enumerate(data.get("findings", []), 1):
        findings_md += f"""
### Finding {i}: {f['title']}

- **Severity:** {f['severity']}
- **CVSS:** {f.get('cvss', 'N/A')}
- **Description:** {f['description']}
- **Evidence:** {f.get('evidence', 'N/A')}
- **Recommendation:** {f['recommendation']}
"""
    return REPORT_TEMPLATE.format(
        client=data.get("client", "CONFIDENTIAL"),
        engagement_id=data.get("engagement_id", "N/A"),
        date=datetime.now().strftime("%Y-%m-%d"),
        operator=data.get("operator", "Unknown"),
        executive_summary=data.get("executive_summary", ""),
        scope_targets="\n".join(data.get("scope_targets", [])),
        findings=findings_md,
        recommendations=data.get("recommendations", ""),
        appendix=data.get("appendix", ""),
    )


def generate_html_report(data: dict) -> str:
    """Generate HTML penetration test report with executive theme."""
    findings_html = ""
    for i, f in enumerate(data.get("findings", []), 1):
        findings_html += f"""
        <div class="finding-card">
            <h3>Finding {i}: {html.escape(f.get('title', ''))}</h3>
            <p><strong>Severity:</strong> <span class="badge {f.get('severity', 'low').lower()}">{html.escape(f.get('severity', ''))}</span></p>
            <p><strong>Description:</strong> {html.escape(f.get('description', ''))}</p>
            <p><strong>Recommendation:</strong> {html.escape(f.get('recommendation', ''))}</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Pentest Report — {html.escape(data.get('client', 'CONFIDENTIAL'))}</title>
    <style>
        body {{ font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; max-width: 900px; margin: 0 auto; }}
        h1 {{ color: #ef4444; border-bottom: 2px solid #334155; padding-bottom: 0.5rem; }}
        .finding-card {{ background: #1e293b; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #ef4444; }}
        .badge {{ padding: 2px 8px; border-radius: 4px; font-weight: bold; }}
        .badge.high, .badge.critical {{ background: #ef4444; color: white; }}
        .badge.medium {{ background: #f59e0b; color: white; }}
        .badge.low {{ background: #10b981; color: white; }}
    </style>
</head>
<body>
    <h1>Security Audit Report</h1>
    <p><b>Client:</b> {html.escape(data.get('client', ''))} | <b>Engagement:</b> {html.escape(data.get('engagement_id', ''))}</p>
    <hr>
    <h2>Findings</h2>
    {findings_html}
</body>
</html>"""
