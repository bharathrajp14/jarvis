# src/brjarvis/apps/cli.py — Canonical CLI Entry Point for BR JARVIS MK40.2+
from __future__ import annotations

import sys
from brjarvis.core.cli import main as cli_main


def main() -> int:
    """Canonical CLI main entry point."""
    try:
        return cli_main()
    except (KeyboardInterrupt, EOFError):
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)
