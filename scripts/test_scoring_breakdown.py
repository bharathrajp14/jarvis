import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.complexity_router import calculate_complexity_score

prompts = [
    ("Greeting", [{"role": "user", "content": "hi"}]),
    ("Simple Query", [{"role": "user", "content": "What is the time?"}]),
    ("Standard Summary", [{"role": "user", "content": "Can you summarize the main architecture features of our JARVIS application for the project documentation report?"}]),
    ("Complex Coding", [{"role": "user", "content": "Write a python function to refactor a binary tree traversal algorithm with error handling:\ndef traverse(node):\n    if not node:\n        return\n    return traverse(node.left) + [node.val] + traverse(node.right)"}]),
    ("Math & Architecture", [{"role": "user", "content": "Derive the mathematical proof for time complexity of quicksort in average case vs worst case, and optimize the pivot selection."}]),
]

if 'logger' in globals() or 'logger' in locals():
    logger.info("=== MULTI-DIMENSIONAL COMPLEXITY SCORING ENGINE REPORT ===")
else:
    import logging
    logging.getLogger(__name__).info("=== MULTI-DIMENSIONAL COMPLEXITY SCORING ENGINE REPORT ===")
for name, msg in prompts:
    score, tier, breakdown = calculate_complexity_score(msg)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"\nPrompt Name: {name}" }" if isinstance(f"\nPrompt Name: {name}", str) else f"\nPrompt Name: {name}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"\nPrompt Name: {name}" }" if isinstance(f"\nPrompt Name: {name}", str) else f"\nPrompt Name: {name}")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  Result Tier: {tier.value.upper()} (Score: {score:.2f}/100)" }" if isinstance(f"  Result Tier: {tier.value.upper()} (Score: {score:.2f}/100)", str) else f"  Result Tier: {tier.value.upper()} (Score: {score:.2f}/100)")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  Result Tier: {tier.value.upper()} (Score: {score:.2f}/100)" }" if isinstance(f"  Result Tier: {tier.value.upper()} (Score: {score:.2f}/100)", str) else f"  Result Tier: {tier.value.upper()} (Score: {score:.2f}/100)")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  Breakdown: {json.dumps(breakdown)}" }" if isinstance(f"  Breakdown: {json.dumps(breakdown)}", str) else f"  Breakdown: {json.dumps(breakdown)}")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  Breakdown: {json.dumps(breakdown)}" }" if isinstance(f"  Breakdown: {json.dumps(breakdown)}", str) else f"  Breakdown: {json.dumps(breakdown)}")
