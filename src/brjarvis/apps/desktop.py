# src/brjarvis/apps/desktop.py — Canonical Desktop GUI / HUD Entry Point for BR JARVIS MK40.2+
from __future__ import annotations

import sys

from brjarvis.ui.app import run_voice_ui


def main() -> int:
    try:
        run_voice_ui()
        return 0
    except Exception as e:
        print(f"Error starting Desktop GUI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
