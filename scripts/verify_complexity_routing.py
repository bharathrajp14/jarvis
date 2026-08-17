
# scripts/verify_complexity_routing.py — Verify Dynamic Model Switching
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("JARVIS.ComplexityRouting")

root_dir = Path(__file__).resolve().parent.parent
for p in [str(root_dir / "src"), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from brjarvis.integrations.backends.gemini import GeminiBackend

logger.info("=== VERIFYING DYNAMIC COMPLEXITY-BASED MODEL SWITCHING ===")

backend = GeminiBackend()

test_cases = [
    ("FAST (Low Latency)", [{"role": "user", "content": "hi"}]),
    ("MEDIUM (Standard Chat)", [{"role": "user", "content": "Summarize how JARVIS processes user queries into action plans."}]),
    ("HIGH (Code & Reasoning)", [{"role": "user", "content": "Write a python function to refactor a binary tree traversal algorithm:\ndef traverse(node):\n    pass"}]),
]

for label, messages in test_cases:
    start = time.time()
    response = backend.complete(messages)
    elapsed = round(time.time() - start, 2)
    logger.info(f"\n[Test: {label}] (Latency: {elapsed}s)")
    logger.info(f"Response snippet: {response[:120]}...")
