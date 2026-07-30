import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backends.gemini import GeminiBackend

print("=== VERIFYING DYNAMIC COMPLEXITY-BASED MODEL SWITCHING ===")

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
    print(f"\n[Test: {label}] (Latency: {elapsed}s)")
    print(f"Response snippet: {response[:120]}...")
