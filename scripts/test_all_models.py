import json
import os
import time
from openai import OpenAI

BASE_URL = "http://127.0.0.1:8045/v1"
API_KEY = os.environ.get("OPENAI_API_KEY", "sk-local")

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)

print("--- Step 1: Checking client.models.list() ---")
try:
    models_list = client.models.list()
    print("Available models in proxy list:")
    for m in models_list.data:
        print(f"  - {m.id}")
except Exception as e:
    print(f"client.models.list() failed: {e}")

models_to_test = [
    "claude-opus-4-6",
    "claude-opus-4-6-thinking",
    "gemini-2.5-flash",
    "gemini-3.1-pro",
    "gemini-3.6-flash-tiered",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-pro",
    "claude-sonnet-4-6",
    "claude-sonnet-4-6-thinking",
    "gemini-3.6-flash-low",
    "gemini-3.6-flash-high",
    "gemini-2.5-flash-thinking",
    "gemini-3.6-flash-medium",
    "gemini-3.1-flash-image",
    "gemini-3.1-pro-high",
    "gemini-3-flash",
    "gemini-3-pro-image",
    "gemini-3.1-pro-low"
]

results = {}

print("\n--- Step 2: Testing individual model completions ---")
for model_id in models_to_test:
    print(f"\nTesting model: {model_id}...")
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Reply with 'OK' and your exact name if working."}],
            max_tokens=50,
            timeout=15.0
        )
        elapsed = round(time.time() - start_time, 2)
        content = response.choices[0].message.content.strip()
        print(f"  [SUCCESS] ({elapsed}s) Response: {content[:100]}")
        results[model_id] = {"status": "SUCCESS", "latency": elapsed, "response": content}
    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        err_msg = str(e)
        print(f"  [FAILED] ({elapsed}s) Error: {err_msg[:150]}")
        results[model_id] = {"status": "FAILED", "latency": elapsed, "error": err_msg}

print("\n=== SUMMARY RESULTS ===")
print(json.dumps(results, indent=2))
