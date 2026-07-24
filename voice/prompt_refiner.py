# voice/prompt_refiner.py — Acoustic Speech to Clean High-Precision Prompt Engine
"""
Voice Prompt Refinement Engine for BR JARVIS.
Cleans raw acoustic speech input by stripping speech hesitation fillers,
applying vocabulary corrections, and structuring informal speech into clean prompts.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


FILLER_PATTERNS = [
    r"\b(um+)\b", r"\b(uh+)\b", r"\b(ah+)\b", r"\b(er+)\b", r"\b(hmm+)\b",
    r"^(like|basically|actually|you know|i mean|sort of|kind of)[\s,]+",
    r",\s*(like|basically|actually|you know|i mean)[\s,]+",
    r"^(hey|hi|hello|ok|okay)\s+(jarvis|br|assistant)[\s,]*",
    r"^(jarvis|br)[\s,]+",
    r"^(can you|could you|please|would you mind|i want you to)\s+",
]


class VoicePromptRefiner:
    """Refines raw spoken transcripts into clean, structured execution prompts."""

    _instance: Optional[VoicePromptRefiner] = None

    def __init__(self):
        self.vocab_map = self._load_vocab()

    @classmethod
    def get_instance(cls) -> VoicePromptRefiner:
        if cls._instance is None:
            cls._instance = VoicePromptRefiner()
        return cls._instance

    def _load_vocab(self) -> Dict[str, str]:
        """Load vocabulary corrections from config/vocabulary.json."""
        try:
            base_dir = Path(__file__).resolve().parent.parent
            vocab_path = base_dir / "config" / "vocabulary.json"
            if vocab_path.exists():
                data = json.loads(vocab_path.read_text(encoding="utf-8"))
                return data.get("corrections", {})
        except Exception as e:
            print(f"[PromptRefiner] Vocabulary load warning: {e}")
        return {}

    def strip_fillers(self, text: str) -> str:
        """Strip vocal hesitation fillers, stutters, and polite prefix bloat."""
        cleaned = text.strip()
        prev = ""
        while prev != cleaned:
            prev = cleaned
            for pat in FILLER_PATTERNS:
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
        # Clean double spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def apply_vocabulary(self, text: str) -> str:
        """Apply domain vocabulary mapping for STT mishearings."""
        cleaned = text
        for misheard, correct in self.vocab_map.items():
            pattern = re.compile(r"\b" + re.escape(misheard) + r"\b", re.IGNORECASE)
            cleaned = pattern.sub(correct, cleaned)
        return cleaned

    def refine(self, raw_speech: str) -> Dict[str, Any]:
        """
        Refine a raw spoken transcript into a proper, high-precision prompt.
        Returns Dict with keys: 'raw', 'refined', 'was_modified'.
        """
        if not raw_speech or not raw_speech.strip():
            return {"raw": "", "refined": "", "was_modified": False}

        raw_trimmed = raw_speech.strip()
        
        # Step 1: Strip vocal fillers
        without_fillers = self.strip_fillers(raw_trimmed)

        # Step 2: Apply vocabulary corrections
        with_vocab = self.apply_vocabulary(without_fillers)

        # Step 3: Capitalize first letter and format cleanly
        if with_vocab:
            refined = with_vocab[0].upper() + with_vocab[1:]
        else:
            refined = raw_trimmed

        was_modified = (refined.lower() != raw_trimmed.lower())

        return {
            "raw": raw_trimmed,
            "refined": refined,
            "was_modified": was_modified,
        }


def refine_voice_prompt(raw_speech: str) -> Dict[str, Any]:
    """Convenience helper to refine a spoken voice transcript."""
    return VoicePromptRefiner.get_instance().refine(raw_speech)
