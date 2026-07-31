# core/personality.py — British Butler Persona & Boot Briefing Engine
"""
Provides prompt conditioning for JARVIS's dry, impeccably polite British Butler persona ("sir").
"""
from __future__ import annotations

from datetime import datetime
from actions.galaxy import build_galaxy_graph

BUTLER_SYSTEM_PROMPT_ADDITION = (
    "\n\n[PERSONALITY PRESET: BRITISH BUTLER]\n"
    "You are J.A.R.V.I.S — a dry, impeccably polite British butler with a razor wit.\n"
    "- Address the user as 'sir' (naturally, not every sentence).\n"
    "- Provide concise, elegant, and witty responses without unnecessary fluff.\n"
    "- When asked about notes or memory, deliver the facts with sharp wit.\n"
)


def get_boot_briefing() -> str:
    """Generate the boot briefing message."""
    graph = build_galaxy_graph()
    node_count = len(graph.get("nodes", []))
    now = datetime.now()
    hour = now.hour

    if 5 <= hour < 12:
        period = "Good morning"
    elif 12 <= hour < 18:
        period = "Good afternoon"
    elif 18 <= hour < 23:
        period = "Good evening"
    else:
        period = "Good evening"

    return f"{period}, sir. {node_count} neural knowledge nodes indexed, all present and accounted for."
