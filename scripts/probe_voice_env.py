"""Voice and audio environment diagnostic tool for BR JARVIS."""
from __future__ import annotations

import sys

libs = [
    'sounddevice',
    'numpy',
    'faster_whisper',
    'whisper',
    'speech_recognition',
    'torch',
    'onnxruntime',
    'pvporcupine',
    'pyaudio',
    'vosk',
    'scipy',
    'webrtcvad',
]


def main() -> int:
    print("\n=== CHECKING VOICE & AUDIO ENVIRONMENT PACKAGES ===")
    missing = 0
    for lib in libs:
        try:
            mod = __import__(lib)
            ver = getattr(mod, '__version__', 'available')
            print(f"  [INSTALLED] {lib:20s}: (version {ver})")
        except Exception as e:
            print(f"  [MISSING]   {lib:20s}: ({e})")
            missing += 1
    print(f"\nAudio probe complete. {len(libs) - missing}/{len(libs)} packages available.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
