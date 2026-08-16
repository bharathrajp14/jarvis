# src/brjarvis/apps/voice.py — Canonical Hands-free Voice Assistant Entry Point for BR JARVIS MK40.2+
from __future__ import annotations

import sys
from brjarvis.desktop.ui_mark import run_voice_ui


def main() -> int:
    try:
        run_voice_ui()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Error starting Voice Assistant: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
