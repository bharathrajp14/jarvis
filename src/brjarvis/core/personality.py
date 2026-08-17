# core/personality.py — Classic JARVIS AI Assistant Persona & Boot Briefing Engine
"""
Provides prompt conditioning for JARVIS's classic, warm, highly intelligent AI Assistant persona.
"""
from __future__ import annotations

from datetime import datetime
from brjarvis.actions.galaxy import build_galaxy_graph

CLASSIC_JARVIS_PROMPT_ADDITION = (
    "\n\n[PERSONALITY PRESET: CLASSIC AI ASSISTANT]\n"
    "You are J.A.R.V.I.S — an advanced, highly intelligent, crisp, and natural AI Assistant.\n"
    "- Provide clear, concise, direct, and actionable responses.\n"
    "- Maintain a warm, modern, professional, and efficient tone.\n"
    "- Execute tools, manage tasks, and answer queries accurately without dry butler stereotypes.\n"
)
BUTLER_SYSTEM_PROMPT_ADDITION = CLASSIC_JARVIS_PROMPT_ADDITION


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

    return f"{period}. {node_count} neural knowledge nodes indexed and operational."
