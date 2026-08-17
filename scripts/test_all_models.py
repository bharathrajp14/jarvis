
# scripts/test_all_models.py — Test All Proxy Models
from __future__ import annotations

import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("JARVIS.TestAllModels")

try:
    from openai import OpenAI
except ImportError:
    logger.error("openai package is not installed. Install with: pip install openai")
    raise SystemExit(1)

BASE_URL = os.environ.get("BRJARVIS_PROXY_BASE_URL", os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8045/v1"))
API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not API_KEY:
    try:
        from pathlib import Path
        cfg_file = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        if cfg_file.exists():
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            API_KEY = data.get("proxy_api_key") or data.get("openai_api_key") or "sk-5ec70bf9fa324084b7a7326babf52c45"
    except Exception:
        API_KEY = "sk-5ec70bf9fa324084b7a7326babf52c45"
API_KEY = API_KEY or "sk-5ec70bf9fa324084b7a7326babf52c45"

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)

logger.info("--- Step 1: Checking client.models.list() ---")
try:
    models_list = client.models.list()
    logger.info("Available models in proxy list:")
    for m in models_list.data:
        logger.info(f"  - {m.id}")
except Exception as e:
    logger.warning(f"client.models.list() failed: {e}")

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

logger.info("\n--- Step 2: Testing individual model completions ---")
for model_id in models_to_test:
    logger.info(f"\nTesting model: {model_id}...")
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
        logger.info(f"  [SUCCESS] ({elapsed}s) Response: {content[:100]}")
        results[model_id] = {"status": "SUCCESS", "latency": elapsed, "response": content}
    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        err_msg = str(e)
        logger.warning(f"  [FAILED] ({elapsed}s) Error: {err_msg[:150]}")
        results[model_id] = {"status": "FAILED", "latency": elapsed, "error": err_msg}

logger.info("\n=== SUMMARY RESULTS ===")
logger.info(json.dumps(results, indent=2))
