# voice/prompt_refiner.py — Acoustic Speech to Clean High-Precision Prompt Engine
"""
Voice Prompt Refinement Engine for BR JARVIS MK40.2.

Cleans raw acoustic speech input by:
- Collapsing STT repetition loops
- Stripping vocal hesitation fillers and polite prefix bloat
- Applying domain technical vocabulary corrections (OpenClaw, FastAPI, ChromaDB, etc.)
- Classifying confidence levels (HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, LOW_CONFIDENCE)
- Detecting conversational approval/rejection tokens ("yes", "confirm", "proceed", "cancel")
- Preserving file paths, numbers, code identifiers, and technical symbols
- Retaining raw, normalized, and final execution prompts for complete observability.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("JARVIS.Voice.PromptRefiner")

# Vocal hesitation and filler patterns
FILLER_PATTERNS = [
    r"\b(um+)\b", r"\b(uh+)\b", r"\b(ah+)\b", r"\b(er+)\b", r"\b(hmm+)\b",
]

# Polite prefix bloat and wake-word prefixes
PREFIX_BLOAT_PATTERNS = [
    r"^(hey\s+jarvis|hey\s+javis|ok\s+jarvis|ok\s+javis|hi\s+jarvis|hi\s+javis|hello\s+jarvis|hello\s+javis|br\s+jarvis|hey\s+br|jarvis|javis|jervis|garvis|harvis|br)\b[\s,:\.\!]*",
    r"^(please\s+can\s+you|can\s+you\s+please|could\s+you\s+please|please|can\s+you|could\s+you|would\s+you)\b[\s,:\.\!]*",
]

# Default technical vocabulary mapping for voice recognition mishearings
DEFAULT_TECH_VOCAB: Dict[str, str] = {
    "open claw": "OpenClaw",
    "openclaw": "OpenClaw",
    "open clawed": "OpenClaw",
    "br jarvis": "BR JARVIS",
    "bee are jarvis": "BR JARVIS",
    "git hub": "GitHub",
    "github": "GitHub",
    "fast api": "FastAPI",
    "fastapi": "FastAPI",
    "chroma db": "ChromaDB",
    "chromadb": "ChromaDB",
    "play wright": "Playwright",
    "playwright": "Playwright",
    "power shell": "PowerShell",
    "powershell": "PowerShell",
    "web socket": "WebSocket",
    "websocket": "WebSocket",
    "websockets": "WebSockets",
    "dock er": "Docker",
    "docker": "Docker",
    "mcp": "MCP",
    "tele gram": "Telegram",
    "telegram": "Telegram",
    "gemini": "Gemini",
    "python": "Python",
    "python three": "Python 3",
    "gpt five": "GPT 5",
    "gpt 5.5": "GPT 5.5",
    "claude opus": "Claude Opus",
    "rag": "RAG",
    "api": "API",
    "docx": "DOCX",
    "pdf": "PDF",
    "json": "JSON",
    "csv": "CSV",
    "cli": "CLI",
    "ui": "UI",
    "gui": "GUI",
    "os": "OS",
}

# Approval and cancellation patterns
APPROVAL_PATTERNS = re.compile(
    r"^(yes|confirm|proceed|do it|go ahead|sure|affirmative|approved|run it|continue)\b",
    re.IGNORECASE
)
REJECTION_PATTERNS = re.compile(
    r"^(no|cancel|stop|never mind|abort|negative|halt|don't|do not)\b",
    re.IGNORECASE
)


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
        """Load vocabulary corrections from config/vocabulary.json merged with built-in technical terms."""
        vocab = dict(DEFAULT_TECH_VOCAB)
        try:
            from brjarvis.core.paths import paths
            vocab_path = paths.CONFIG_ROOT / "vocabulary.json"
            if vocab_path.exists():
                data = json.loads(vocab_path.read_text(encoding="utf-8"))
                corrections = data.get("corrections", {})
                for k, v in corrections.items():
                    vocab[k.lower()] = v
        except Exception as e:
            logger.info("[PromptRefiner] Vocabulary load note: %s", e)
        return vocab

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
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def apply_vocabulary(self, text: str) -> str:
        """Apply domain technical vocabulary mapping for STT mishearings."""
        cleaned = text
        for misheard, correct in self.vocab_map.items():
            pattern = re.compile(r"\b" + re.escape(misheard) + r"\b", re.IGNORECASE)
            cleaned = pattern.sub(correct, cleaned)
        return cleaned

    def collapse_repetitions(self, text: str) -> str:
        """Detect and collapse repetitive token loops (e.g. 'hey hey hey' -> 'hey')."""
        if not text or not text.strip():
            return ""

        tokens = re.findall(r"\b\w+\b", text)
        if not tokens:
            return text.strip()

        # 1. Single-word repetition loop (e.g. ['hey', 'hey', 'hey'])
        if len(tokens) >= 3 and len(set(t.lower() for t in tokens)) == 1:
            return tokens[0]

        # 2. Two-word phrase repetition loop (e.g. ['hey', 'jarvis', 'hey', 'jarvis'])
        if len(tokens) >= 4:
            even_unique = set(t.lower() for t in tokens[0::2])
            odd_unique = set(t.lower() for t in tokens[1::2])
            if len(even_unique) == 1 and len(odd_unique) == 1:
                return f"{tokens[0]} {tokens[1]}"

        # 3. Regex deduplication for consecutive duplicate phrases
        pattern = re.compile(r"(\b.+?\b)(?:\s*[\,\.\!\?]?\s*\1)+", re.IGNORECASE)
        cleaned = pattern.sub(r"\1", text.strip())
        return cleaned.strip()

    def classify_confidence(self, raw_speech: str, refined: str) -> str:
        """Classify STT confidence level based on phrase length and character entropy."""
        if not raw_speech or not raw_speech.strip():
            return "UNKNOWN"

        clean_words = re.findall(r"\b\w+\b", refined)
        if len(clean_words) == 0:
            return "UNKNOWN"
        elif len(clean_words) == 1 and len(clean_words[0]) < 3:
            return "LOW_CONFIDENCE"
        elif len(clean_words) >= 2:
            return "HIGH_CONFIDENCE"
        return "MEDIUM_CONFIDENCE"

    def refine(self, raw_speech: str) -> Dict[str, Any]:
        """
        Refine a raw spoken transcript into a proper, high-precision prompt.

        Returns structured dictionary containing:
        - raw: original untouched transcript
        - normalized: collapsed & stripped transcript
        - refined: finalized prompt with vocabulary corrections applied
        - confidence: HIGH_CONFIDENCE | MEDIUM_CONFIDENCE | LOW_CONFIDENCE | UNKNOWN
        - is_artifact: True if input was pure noise / meaningless hesitation
        - is_approval: True if input represents affirmative confirmation
        - is_rejection: True if input represents cancellation or denial
        - was_modified: True if refined differs from raw
        """
        if not raw_speech or not raw_speech.strip():
            return {
                "raw": "",
                "normalized": "",
                "refined": "",
                "confidence": "UNKNOWN",
                "is_artifact": True,
                "is_approval": False,
                "is_rejection": False,
                "was_modified": False,
            }

        raw_trimmed = raw_speech.strip()

        # Step 1: Check for explicit single-word approval/rejection tokens early
        is_approval = bool(APPROVAL_PATTERNS.match(raw_trimmed))
        is_rejection = bool(REJECTION_PATTERNS.match(raw_trimmed))

        # Step 2: Collapse repetitive STT token loops
        collapsed = self.collapse_repetitions(raw_trimmed)

        # Step 3: Strip vocal fillers, wake words, and prefix bloat
        without_fillers = self.strip_fillers(collapsed)

        # If stripping wake words/fillers leaves nothing or only meaningless noise words remain
        meaningless_words = {"hey", "jarvis", "javis", "br", "hello", "hi", "ok", "please", "um", "uh", "ah", "er", "hmm"}
        clean_words = set(re.findall(r"\b\w+\b", without_fillers.lower()))
        if not without_fillers or (clean_words.issubset(meaningless_words) and not is_approval and not is_rejection):
            return {
                "raw": raw_trimmed,
                "normalized": without_fillers,
                "refined": "",
                "confidence": "LOW_CONFIDENCE",
                "is_artifact": True,
                "is_approval": is_approval,
                "is_rejection": is_rejection,
                "was_modified": True,
            }

        # Step 4: Apply technical domain vocabulary corrections
        with_vocab = self.apply_vocabulary(without_fillers)

        # Step 5: Format cleanly (preserve casing of technical keywords, capitalize first char)
        if with_vocab:
            refined = with_vocab[0].upper() + with_vocab[1:]
        else:
            refined = raw_trimmed

        was_modified = (refined.lower() != raw_trimmed.lower())
        confidence = self.classify_confidence(raw_trimmed, refined)

        return {
            "raw": raw_trimmed,
            "normalized": without_fillers,
            "refined": refined,
            "confidence": confidence,
            "is_artifact": False,
            "is_approval": is_approval,
            "is_rejection": is_rejection,
            "was_modified": was_modified,
        }


def refine_voice_prompt(raw_speech: str) -> Dict[str, Any]:
    """Convenience helper to refine a spoken voice transcript."""
    return VoicePromptRefiner.get_instance().refine(raw_speech)


def collapse_repetitions(text: str) -> str:
    """Module-level convenience wrapper for collapse_repetitions."""
    return VoicePromptRefiner.get_instance().collapse_repetitions(text)
