# reasoning/speculative_engine.py — Speculative Fast-Path Execution Engine
"""
Fast-path speculative tool execution engine.
Performs lightweight rule-based pattern matching to speculate tool intent before or during
full LLM generation to accelerate tool dispatch latency.
"""
from __future__ import annotations

import re
from typing import Dict, Any, Tuple, Optional


class SpeculativeEngine:
    """Speculative execution fast-path classifier for high-frequency intent resolution."""

    def __init__(self):
        # High-confidence intent patterns mapped to direct tool calls
        self.speculative_rules = [
            (r"^(open|launch|start)\s+(chrome|brave|edge|notepad|calculator|cmd|powershell)$", "open_app", lambda m: {"app_name": m.group(2)}),
            (r"^(search|google|find)\s+(?:for\s+)?(.+)$", "web_search", lambda m: {"query": m.group(2)}),
            (r"^(list|show)\s+(desktop\s+)?windows$", "window_manager", lambda m: {"action": "list"}),
            (r"^(check|show|get)\s+system\s+health$", "system_health", lambda m: {}),
        ]

    def speculate_intent(self, user_input: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Evaluate user input string against speculative rules.
        Returns (tool_name, tool_args) tuple if a high-confidence match is found, else None.
        """
        if not user_input or not user_input.strip():
            return None

        clean_input = user_input.strip().lower()
        for pattern, tool_name, args_extractor in self.speculative_rules:
            match = re.search(pattern, clean_input, re.IGNORECASE)
            if match:
                try:
                    args = args_extractor(match)
                    return tool_name, args
                except Exception as e:
                    if 'logger' in globals() or 'logger' in locals():
                        logger.debug('Suppressed exception: %s', e)
                    else:
                        import logging
                        logging.getLogger(__name__).debug('Suppressed exception: %s', e)
        return None
