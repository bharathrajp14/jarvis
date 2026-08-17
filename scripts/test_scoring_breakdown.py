
# scripts/test_scoring_breakdown.py — Multi-Dimensional Complexity Scoring Report
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("JARVIS.ScoringBreakdown")

root_dir = Path(__file__).resolve().parent.parent
for p in [str(root_dir / "src"), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from brjarvis.config.complexity_router import calculate_complexity_score

prompts = [
    ("Greeting", [{"role": "user", "content": "hi"}]),
    ("Simple Query", [{"role": "user", "content": "What is the time?"}]),
    ("Standard Summary", [{"role": "user", "content": "Can you summarize the main architecture features of our JARVIS application for the project documentation report?"}]),
    ("Complex Coding", [{"role": "user", "content": "Write a python function to refactor a binary tree traversal algorithm with error handling:\ndef traverse(node):\n    if not node:\n        return\n    return traverse(node.left) + [node.val] + traverse(node.right)"}]),
    ("Math & Architecture", [{"role": "user", "content": "Derive the mathematical proof for time complexity of quicksort in average case vs worst case, and optimize the pivot selection."}]),
]

logger.info("=== MULTI-DIMENSIONAL COMPLEXITY SCORING ENGINE REPORT ===")
for name, msg in prompts:
    score, tier, breakdown = calculate_complexity_score(msg)
    logger.info(f"\nPrompt Name: {name}")
    logger.info(f"  Result Tier: {tier.value.upper()} (Score: {score:.2f}/100)")
    logger.info(f"  Breakdown: {json.dumps(breakdown)}")
