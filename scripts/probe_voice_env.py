
import logging
import sys

logger = logging.getLogger(__name__)

libs = ['sounddevice', 'numpy', 'faster_whisper', 'whisper', 'speech_recognition', 'torch', 'onnxruntime', 'pvporcupine', 'pyaudio', 'vosk', 'scipy', 'webrtcvad']

logger.info("=== CHECKING VOICE & AUDIO ENVIRONMENT PACKAGES ===")
for lib in libs:
    try:
        mod = __import__(lib)
        ver = getattr(mod, '__version__', 'available')
        logger.info(f"  [INSTALLED] {lib:20s}: (version {ver})")
    except Exception as e:
        logger.info(f"  [MISSING]   {lib:20s}: ({e})")
