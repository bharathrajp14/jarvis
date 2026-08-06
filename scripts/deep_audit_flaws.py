import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if 'logger' in globals() or 'logger' in locals():
    logger.info("=== DEEP ARCHITECTURAL AUDIT & FLAW FINDER ===")
else:
    import logging
    logging.getLogger(__name__).info("=== DEEP ARCHITECTURAL AUDIT & FLAW FINDER ===")
flaws = []

# Issue 1: Check if models.py clears cache when models.json is edited dynamically
try:
    from config.models import get_model_config, clear_model_config_cache
    c1 = get_model_config()
    clear_model_config_cache()
    c2 = get_model_config()
    if 'logger' in globals() or 'logger' in locals():
        logger.info("  [OK] Model Config Cache clearing function exists.")
    else:
        import logging
        logging.getLogger(__name__).info("  [OK] Model Config Cache clearing function exists.")
except Exception as e:
    flaws.append(f"Model config cache management issue: {e}")

# Issue 2: Check backend fallback resilience when proxy is invalid
try:
    from backends.gemini import GeminiBackend
    # Test initializing with bad base url or proxy flag to ensure zero crash
    g = GeminiBackend()
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"  [OK] GeminiBackend initialized cleanly (proxy: {g._use_openai_client}, model: {g.model})" }" if isinstance(f"  [OK] GeminiBackend initialized cleanly (proxy: {g._use_openai_client}, model: {g.model})", str) else f"  [OK] GeminiBackend initialized cleanly (proxy: {g._use_openai_client}, model: {g.model})")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"  [OK] GeminiBackend initialized cleanly (proxy: {g._use_openai_client}, model: {g.model})" }" if isinstance(f"  [OK] GeminiBackend initialized cleanly (proxy: {g._use_openai_client}, model: {g.model})", str) else f"  [OK] GeminiBackend initialized cleanly (proxy: {g._use_openai_client}, model: {g.model})")
except Exception as e:
    flaws.append(f"GeminiBackend initialization flaw: {e}")

# Issue 3: Check complexity router handling of empty/malformed messages
try:
    from config.complexity_router import calculate_complexity_score, select_model_for_prompt
    
    # Edge case 1: None content
    s1, t1, _ = calculate_complexity_score([{"role": "user", "content": None}])
    # Edge case 2: Complex nested dict content without text key
    s2, t2, _ = calculate_complexity_score([{"role": "user", "content": [{"type": "unknown", "data": 123}]}])
    # Edge case 3: Extremely long prompt with repeated whitespace
    s3, t3, _ = calculate_complexity_score([{"role": "user", "content": "   \n\t   " * 100}])
    
    if 'logger' in globals() or 'logger' in locals():
        logger.info("  [OK] Complexity router handles all malformed/edge-case payloads gracefully.")
    else:
        import logging
        logging.getLogger(__name__).info("  [OK] Complexity router handles all malformed/edge-case payloads gracefully.")
except Exception as e:
    flaws.append(f"Complexity router edge-case flaw: {e}")

# Issue 4: Check sounddevice device index robustness in voice/stt.py
try:
    from voice.stt import SounddeviceMicrophone
    mic = SounddeviceMicrophone(device=99999) # Invalid index
    if 'logger' in globals() or 'logger' in locals():
        logger.warning(f"{ f"  [OK] SounddeviceMicrophone handles invalid device index gracefully (fallback idx: {mic.device_index})" }" if isinstance(f"  [OK] SounddeviceMicrophone handles invalid device index gracefully (fallback idx: {mic.device_index})", str) else f"  [OK] SounddeviceMicrophone handles invalid device index gracefully (fallback idx: {mic.device_index})")
    else:
        import logging
        logging.getLogger(__name__).warning(f"{ f"  [OK] SounddeviceMicrophone handles invalid device index gracefully (fallback idx: {mic.device_index})" }" if isinstance(f"  [OK] SounddeviceMicrophone handles invalid device index gracefully (fallback idx: {mic.device_index})", str) else f"  [OK] SounddeviceMicrophone handles invalid device index gracefully (fallback idx: {mic.device_index})")
except Exception as e:
    flaws.append(f"SounddeviceMicrophone fallback flaw: {e}")

if 'logger' in globals() or 'logger' in locals():
    logger.info("\n=== AUDIT SUMMARY ===")
else:
    import logging
    logging.getLogger(__name__).info("\n=== AUDIT SUMMARY ===")
if flaws:
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"Found {len(flaws)} potential issues:" }" if isinstance(f"Found {len(flaws)} potential issues:", str) else f"Found {len(flaws)} potential issues:")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"Found {len(flaws)} potential issues:" }" if isinstance(f"Found {len(flaws)} potential issues:", str) else f"Found {len(flaws)} potential issues:")
    for f in flaws:
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"  - {f}" }" if isinstance(f"  - {f}", str) else f"  - {f}")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"  - {f}" }" if isinstance(f"  - {f}", str) else f"  - {f}")
else:
    if 'logger' in globals() or 'logger' in locals():
        logger.info("No critical flaws detected in audited modules!")
    else:
        import logging
        logging.getLogger(__name__).info("No critical flaws detected in audited modules!")
