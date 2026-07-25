# main.py
"""
BR Voice Assistant (main.py v4.1)
Hands-free voice assistant utilizing centralized voice packages.
"""
from __future__ import annotations

import warnings
warnings.simplefilter("ignore")
import asyncio
import os
import sys
import threading
from pathlib import Path

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Setup UTF-8
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load .env
try:
    from dotenv import load_dotenv  # type: ignore
    _env = Path(__file__).resolve().parent / ".env"
    if _env.exists():
        load_dotenv(_env)
except ImportError:
    pass

from ui import JarvisUI
from voice.assistant import BRVoiceAssistant


def main():
    """Main entry point initializing Tkinter HUD and running Voice Assistant worker."""
    ui = JarvisUI("face.png")

    def runner():
        try:
            br = BRVoiceAssistant(ui)
            asyncio.run(br.run())
        except (KeyboardInterrupt, SystemExit):
            print("\n🔴 Shutting down...")
        except Exception as err:
            print(f"[Main Runner Error]: {err}")
            if ui:
                ui.write_log(f"ERR: Voice assistant worker failed: {err}")

    threading.Thread(target=runner, daemon=True).start()
    try:
        ui.root.mainloop()
    except (KeyboardInterrupt, SystemExit):
        print("\n[JARVIS] 👋 Voice Assistant GUI closed.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("\n[JARVIS] 👋 Exited cleanly.")
        sys.exit(0)
