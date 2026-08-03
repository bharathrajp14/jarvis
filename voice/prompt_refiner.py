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
]

PREFIX_BLOAT_PATTERNS = [
    r"^(hey\s+jarvis|hey\s+javis|ok\s+jarvis|ok\s+javis|hi\s+jarvis|hi\s+javis|hello\s+jarvis|hello\s+javis|br\s+jarvis|hey\s+br|jarvis|javis|jervis|garvis|harvis|br)\b[\s,:\.\!]*",
    r"^(please\s+can\s+you|can\s+you\s+please|could\s+you\s+please|please|can\s+you|could\s+you|would\s+you)\b[\s,:\.\!]*",
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
        """Strip vocal hesitation fillers, stutters, wake words, and polite prefix bloat."""
        cleaned = text.strip()
        prev = ""
        while prev != cleaned:
            prev = cleaned
            for pat in FILLER_PATTERNS:
                cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()
            for pat in PREFIX_BLOAT_PATTERNS:
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

    def collapse_repetitions(self, text: str) -> str:
        """Detect and collapse repetitive token loops (e.g. 'hey hey hey' -> 'hey', 'hey javis hey javis' -> 'hey javis')."""
        if not text or not text.strip():
            return ""
        
        tokens = re.findall(r"\b\w+\b", text)
        if not tokens:
            return text.strip()
        
        # 1. Check single-word repetition loop (e.g. ['hey', 'hey', 'hey', ...])
        if len(tokens) >= 3 and len(set(t.lower() for t in tokens)) == 1:
            return tokens[0]

        # 2. Check 2-word phrase repetition loop (e.g. ['hey', 'javis', 'hey', 'javis', ...])
        if len(tokens) >= 4:
            even_unique = set(t.lower() for t in tokens[0::2])
            odd_unique = set(t.lower() for t in tokens[1::2])
            if len(even_unique) == 1 and len(odd_unique) == 1:
                return f"{tokens[0]} {tokens[1]}"

        # 3. Regex deduplication for consecutive duplicate phrases
        pattern = re.compile(r"(\b.+?\b)(?:\s*[\,\.\!\?]?\s*\1)+", re.IGNORECASE)
        cleaned = pattern.sub(r"\1", text.strip())
        return cleaned.strip()

    def refine(self, raw_speech: str) -> Dict[str, Any]:
        """
        Refine a raw spoken transcript into a proper, high-precision prompt.
        Returns Dict with keys: 'raw', 'refined', 'was_modified'.
        """
        if not raw_speech or not raw_speech.strip():
            return {"raw": "", "refined": "", "was_modified": False}

        raw_trimmed = raw_speech.strip()
        
        # Step 1: Collapse repetitive STT token loops
        collapsed = self.collapse_repetitions(raw_trimmed)

        # Step 2: Strip vocal fillers, wake words, and prefix bloat
        without_fillers = self.strip_fillers(collapsed)

        # If stripping wake words/fillers leaves nothing or only meaningless noise words remain
        meaningless_words = {"hey", "jarvis", "javis", "br", "hello", "hi", "ok", "please", "um", "uh", "ah", "er", "hmm"}
        clean_words = set(re.findall(r"\b\w+\b", without_fillers.lower()))
        if not without_fillers or clean_words.issubset(meaningless_words):
            return {
                "raw": raw_trimmed,
                "refined": "",
                "was_modified": True,
                "is_artifact": True
            }

        # Step 3: Apply vocabulary corrections
        with_vocab = self.apply_vocabulary(without_fillers)

        # Step 4: Capitalize first letter and format cleanly
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


def collapse_repetitions(text: str) -> str:
    """Module-level convenience wrapper for collapse_repetitions (used by whisper_local.py)."""
    return VoicePromptRefiner.get_instance().collapse_repetitions(text)
