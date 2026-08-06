import sys

libs = ['sounddevice', 'numpy', 'faster_whisper', 'whisper', 'speech_recognition', 'torch', 'onnxruntime', 'pvporcupine', 'pyaudio', 'vosk', 'scipy', 'webrtcvad']

if 'logger' in globals() or 'logger' in locals():
    logger.info("=== CHECKING VOICE & AUDIO ENVIRONMENT PACKAGES ===")
else:
    import logging
    logging.getLogger(__name__).info("=== CHECKING VOICE & AUDIO ENVIRONMENT PACKAGES ===")
for lib in libs:
    try:
        mod = __import__(lib)
        ver = getattr(mod, '__version__', 'available')
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"  [INSTALLED] {lib:20s}: (version {ver})" }" if isinstance(f"  [INSTALLED] {lib:20s}: (version {ver})", str) else f"  [INSTALLED] {lib:20s}: (version {ver})")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"  [INSTALLED] {lib:20s}: (version {ver})" }" if isinstance(f"  [INSTALLED] {lib:20s}: (version {ver})", str) else f"  [INSTALLED] {lib:20s}: (version {ver})")
    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"  [MISSING]   {lib:20s}: ({e})" }" if isinstance(f"  [MISSING]   {lib:20s}: ({e})", str) else f"  [MISSING]   {lib:20s}: ({e})")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"  [MISSING]   {lib:20s}: ({e})" }" if isinstance(f"  [MISSING]   {lib:20s}: ({e})", str) else f"  [MISSING]   {lib:20s}: ({e})")
