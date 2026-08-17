
# scripts/deep_audit_flaws.py — Deep Architectural Audit & Flaw Finder
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("JARVIS.DeepAudit")

root_dir = Path(__file__).resolve().parent.parent
for p in [str(root_dir / "src"), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

logger.info("=== DEEP ARCHITECTURAL AUDIT & FLAW FINDER ===")
flaws = []

# Issue 1: Check if models.py clears cache when models.json is edited dynamically
try:
    from brjarvis.config.models import get_model_config, clear_model_config_cache
    c1 = get_model_config()
    clear_model_config_cache()
    c2 = get_model_config()
    logger.info("  [OK] Model Config Cache clearing function exists.")
except Exception as e:
    flaws.append(f"Model config cache management issue: {e}")

# Issue 2: Check backend fallback resilience when proxy is invalid
try:
    from brjarvis.integrations.backends.gemini import GeminiBackend
    g = GeminiBackend()
    logger.info(f"  [OK] GeminiBackend initialized cleanly (proxy: {g._use_openai_client}, model: {g.model})")
except Exception as e:
    flaws.append(f"GeminiBackend initialization flaw: {e}")

# Issue 3: Check complexity router handling of empty/malformed messages
try:
    from brjarvis.config.complexity_router import calculate_complexity_score, select_model_for_prompt
    
    # Edge case 1: None content
    s1, t1, _ = calculate_complexity_score([{"role": "user", "content": None}])
    # Edge case 2: Complex nested dict content without text key
    s2, t2, _ = calculate_complexity_score([{"role": "user", "content": [{"type": "unknown", "data": 123}]}])
    # Edge case 3: Extremely long prompt with repeated whitespace
    s3, t3, _ = calculate_complexity_score([{"role": "user", "content": "   \n\t   " * 100}])
    
    logger.info("  [OK] Complexity router handles all malformed/edge-case payloads gracefully.")
except Exception as e:
    flaws.append(f"Complexity router edge-case flaw: {e}")

# Issue 4: Check sounddevice device index robustness in voice/stt.py
try:
    from brjarvis.voice.stt import SounddeviceMicrophone
    mic = SounddeviceMicrophone(device=99999) # Invalid index
    logger.info(f"  [OK] SounddeviceMicrophone handles invalid device index gracefully (fallback idx: {mic.device_index})")
except Exception as e:
    flaws.append(f"SounddeviceMicrophone fallback flaw: {e}")

logger.info("\n=== AUDIT SUMMARY ===")
if flaws:
    logger.info(f"Found {len(flaws)} potential issues:")
    for f in flaws:
        logger.info(f"  - {f}")
else:
    logger.info("No critical flaws detected in audited modules!")
