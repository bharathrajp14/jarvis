# tools/web_extractor.py — Web Content & Article Extractor Tool for JARVIS
"""
High-speed HTML parsing and web content extraction tool.
Fetches web pages, strips HTML tags, extracts main article content, headers, and metadata.
"""
from __future__ import annotations

import re
import urllib.request
from typing import Dict, Any


def extract_web_content(url: str, max_chars: int = 4000) -> str:
    """Fetch URL and extract clean main text content."""
    if not url or not url.strip():
        return "Error: URL parameter is required."

    target_url = url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

    try:
        req = urllib.request.Request(target_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Strip scripts, styles, and HTML tags
        text = re.sub(r"<(script|style).*?>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<.*?>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[... content truncated to {max_chars} chars ...]"

        return f"Web Content Extracted from {target_url}:\n\n{text}"

    except Exception as e:
        return f"Error extracting content from '{url}': {e}"


def web_extractor_action(args: Dict[str, Any]) -> str:
    """Main tool handler for web extraction."""
    url = str(args.get("url", "")).strip()
    return extract_web_content(url)
