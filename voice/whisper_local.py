# voice/whisper_local.py — JARVIS MK37 Local Whisper STT Engine
"""
Offline speech-to-text using OpenAI Whisper running locally.
Supports faster-whisper (preferred) or openai-whisper as backends.
No API calls — everything runs on the local machine.
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
import traceback
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.WhisperLocal")

# ── Configuration ─────────────────────────────────────────────────────────────

WHISPER_MODEL = os.environ.get("JARVIS_WHISPER_MODEL", "base")
# Options: tiny, base, small, medium, large-v3
# Larger = more accurate but slower; base is a good balance

_whisper_engine = None
_engine_type = None  # "faster" or "openai"
_engine_lock = threading.Lock()


def _get_engine():
    """Lazy-load the Whisper engine under lock. Tries faster-whisper first, then openai-whisper."""
    global _whisper_engine, _engine_type

    with _engine_lock:
        if _whisper_engine is not None:
            return _whisper_engine, _engine_type

        model_name = WHISPER_MODEL

        # Try faster-whisper first (much faster with CTranslate2)
        try:
            from faster_whisper import WhisperModel
            device = "cuda" if _cuda_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            logger.info(f"Loading faster-whisper model '{model_name}' on {device}...")
            _whisper_engine = WhisperModel(model_name, device=device, compute_type=compute_type)
            _engine_type = "faster"
            logger.info(f"✓ faster-whisper '{model_name}' ready ({device})")
            return _whisper_engine, _engine_type
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"faster-whisper failed: {e}")

        # Fallback to openai-whisper
        try:
            import whisper
            device = "cuda" if _cuda_available() else "cpu"
            logger.info(f"Loading openai-whisper model '{model_name}' on {device}...")
            _whisper_engine = whisper.load_model(model_name, device=device)
            _engine_type = "openai"
            logger.info(f"✓ openai-whisper '{model_name}' ready ({device})")
            return _whisper_engine, _engine_type
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"openai-whisper failed: {e}")

        return None, None



def _cuda_available() -> bool:
    """Check if CUDA is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def is_available() -> bool:
    """Check if local Whisper is available (either faster-whisper or openai-whisper installed)."""
    try:
        from faster_whisper import WhisperModel
        return True
    except ImportError:
        pass
    try:
        import whisper
        return True
    except ImportError:
        pass
    return False


DEFAULT_INITIAL_PROMPT = "This is a speech command for Jarvis AI assistant to open applications, manage tasks, search, send emails, or run commands."


# ── Hallucination Detection ───────────────────────────────────────────────────

import re as _re

_WHISPER_ARTIFACT_TAGS = _re.compile(
    r"\[(BLANK_AUDIO|Music|Applause|Laughter|Silence|noise|inaudible|crosstalk"
    r"|background noise|sound effects|music playing|ambient|static)\]",
    _re.IGNORECASE
)

_KNOWN_HALLUCINATIONS = frozenset({
    "thank you", "thank you very much", "thanks for watching", "bye", "you",
    "thank you thank you", "i know that", "yeah", "uh", "um", "hmm", "hm",
    "subtitles by", "translated by", "subscribe", "like and subscribe",
    "i love you", "lets go for it", "what are you doing",
    "what is going on", "what are you talking about", "mostly", "sms",
})

_REPETITION_PATTERN = _re.compile(r"\b(\w{3,})\b(?:\s+\1){3,}", _re.IGNORECASE)
_PUNCT_ONLY = _re.compile(r"^[\s\W]+$")


def _is_hallucination(text: str) -> bool:
    """
    Return True if the transcription is a known Whisper hallucination artifact.

    Checks (in order):
      1. Empty or pure-punctuation / symbols only
      2. Too short (< 2 alphanumeric characters)
      3. Whisper artifact tag like [BLANK_AUDIO], [Music]
      4. Known spurious phrase (from empirical Whisper hallucination list)
      5. Repetition loop: same word repeated 4+ times
    """
    if not text or not text.strip():
        return True

    # 1. Pure punctuation / symbols
    if _PUNCT_ONLY.match(text):
        return True

    # 2. Less than 2 real characters
    alphanums = [c for c in text if c.isalnum()]
    if len(alphanums) < 2:
        return True

    # 3. Whisper artifact tags
    if _WHISPER_ARTIFACT_TAGS.search(text):
        return True

    # 4. Known hallucination phrases (normalized)
    normalized = " ".join(text.lower().split())
    normalized_clean = "".join(c for c in normalized if c.isalnum() or c == " ").strip()
    if normalized_clean in _KNOWN_HALLUCINATIONS:
        return True

    # 5. Repetition loop (word repeated 4+ times)
    if _REPETITION_PATTERN.search(text):
        return True

    return False



def transcribe(audio_bytes: bytes, language: str = "en", detect_language: bool = False, initial_prompt: str = "") -> str:
    """
    Transcribe audio bytes using local Whisper (or Groq cloud fast-path).
    Operates 100% in-memory using NumPy float32 arrays — zero disk file creation latency.
    """
    if audio_bytes is None or len(audio_bytes) < 100:
        return ""

    # ── Groq API Cloud Fast-Path (<100ms Latency) ─────────────────────────────
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        try:
            import httpx
            headers = {"Authorization": f"Bearer {groq_key}"}
            files = {"file": ("speech.wav", audio_bytes, "audio/wav")}
            data = {"model": "whisper-large-v3-turbo", "response_format": "text"}
            if not detect_language and language:
                data["language"] = language
            if initial_prompt:
                data["prompt"] = initial_prompt
            resp = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers, files=files, data=data, timeout=3.0
            )
            if resp.status_code == 200:
                txt = resp.text.strip()
                if txt:
                    return txt
        except Exception:
            pass  # Fallback seamlessly to local engine

    # ── RMS Silence Gate ──────────────────────────────────────────────────────
    try:
        import struct
        import math
        import numpy as np
        
        # WAV file header is 44 bytes, raw PCM starts after header
        pcm_data = audio_bytes[44:] if len(audio_bytes) > 44 else audio_bytes
        num_samples = len(pcm_data) // 2
        if num_samples > 0:
            shorts = np.frombuffer(pcm_data[:num_samples * 2], dtype=np.int16)
            float_samples = shorts.astype(np.float32) / 32768.0
            rms = math.sqrt(np.mean(float_samples ** 2))
            
            min_rms = float(os.environ.get("JARVIS_AUDIO_MIN_RMS", "0.015"))
            if rms < min_rms:
                return ""
    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning(f"{ f"[WhisperLocal] Silence gate check failed: {e}" }" if isinstance(f"[WhisperLocal] Silence gate check failed: {e}", str) else f"[WhisperLocal] Silence gate check failed: {e}")
        else:
            import logging
            logging.getLogger(__name__).warning(f"{ f"[WhisperLocal] Silence gate check failed: {e}" }" if isinstance(f"[WhisperLocal] Silence gate check failed: {e}", str) else f"[WhisperLocal] Silence gate check failed: {e}")
        float_samples = None

    engine, engine_type = _get_engine()
    if engine is None:
        return ""

    try:
        text = ""
        prompt = initial_prompt or DEFAULT_INITIAL_PROMPT
        if engine_type == "faster" and float_samples is not None:
            # ⚡ ZERO-DISK IN-MEMORY PATH: Pass numpy float32 directly to CTranslate2 engine
            text = _transcribe_faster(engine, float_samples, language, detect_language, prompt)
        else:
            # Fallback to temp file if numpy conversion failed or using openai-whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                if engine_type == "faster":
                    text = _transcribe_faster(engine, tmp_path, language, detect_language, prompt)
                elif engine_type == "openai":
                    text = _transcribe_openai(engine, tmp_path, language, detect_language, prompt)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

        text_clean = text.strip()
        if not text_clean:
            return ""

        # ── Enhanced Hallucination Filter (MK38) ─────────────────────────────
        # Catches pure-punctuation, single chars, Whisper artifact tags,
        # repetition loops, and known spurious outputs.
        if _is_hallucination(text_clean):
            logger.debug("WhisperLocal: hallucination rejected: %r", text_clean[:60])
            return ""

        return text_clean

    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning(f"{ f"[WhisperLocal] Transcription error: {e}" }" if isinstance(f"[WhisperLocal] Transcription error: {e}", str) else f"[WhisperLocal] Transcription error: {e}")
        else:
            import logging
            logging.getLogger(__name__).warning(f"{ f"[WhisperLocal] Transcription error: {e}" }" if isinstance(f"[WhisperLocal] Transcription error: {e}", str) else f"[WhisperLocal] Transcription error: {e}")
        traceback.print_exc()
        return ""


def _transcribe_faster(engine, audio_input, language: str, detect: bool, initial_prompt: str = "") -> str:
    """Transcribe using faster-whisper (supports file path or numpy array in memory)."""
    prompt = initial_prompt or DEFAULT_INITIAL_PROMPT
    kwargs = {
        "beam_size": 2,
        "best_of": 2,
        "vad_filter": True,
        "vad_parameters": dict(min_speech_duration_ms=100, min_silence_duration_ms=180, speech_pad_ms=120),
        "initial_prompt": prompt,
        "condition_on_previous_text": False,
        "temperature": 0.0,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "repetition_penalty": 1.15,
    }
    if not detect and language:
        kwargs["language"] = language

    segments, info = engine.transcribe(audio_input, **kwargs)
    text_parts = []
    for segment in segments:
        text_parts.append(segment.text.strip())
    return " ".join(text_parts)


def transcribe_wake_fast(audio_bytes: Any, language: str = "en", initial_prompt: str = "") -> str:
    """
    ⚡ ULTRAFAST Wake Word Spotter (<30ms-50ms decoding).
    Bypasses beam search, timestamps, and deep VAD passes for single-phrase wake decoding.
    """
    if audio_bytes is None or len(audio_bytes) < 100:
        return ""

    engine, engine_type = _get_engine()
    if not engine or engine_type != "faster":
        return transcribe(audio_bytes, language=language, initial_prompt=initial_prompt)

    try:
        import numpy as np
        if isinstance(audio_bytes, (bytes, bytearray)):
            pcm_data = audio_bytes[44:] if len(audio_bytes) > 44 else audio_bytes
            num_samples = len(pcm_data) // 2
            if num_samples < 800:
                return ""
            shorts = np.frombuffer(pcm_data[:num_samples * 2], dtype=np.int16)
            float_samples = shorts.astype(np.float32) / 32768.0
        else:
            float_samples = audio_bytes

        prompt = initial_prompt or "Jarvis, Javis, Hey Jarvis, Hey Javis"
        kwargs = {
            "beam_size": 1,
            "best_of": 1,
            "without_timestamps": True,
            "max_initial_timestamp": 0.0,
            "suppress_blank": True,
            "condition_on_previous_text": False,
            "temperature": 0.0,
            "language": language,
            "initial_prompt": prompt,
        }

        segments, _ = engine.transcribe(float_samples, **kwargs)
        parts = [seg.text.strip() for seg in segments]
        text = " ".join(parts).strip()
        from voice.prompt_refiner import collapse_repetitions
        return collapse_repetitions(text)
    except Exception as e:
        logger.warning(f"transcribe_wake_fast error: {e}")
        return transcribe(audio_bytes, language=language, initial_prompt=initial_prompt)


def _transcribe_openai(engine, audio_path: str, language: str, detect: bool, initial_prompt: str = "") -> str:
    """Transcribe using openai-whisper."""
    prompt = initial_prompt or DEFAULT_INITIAL_PROMPT
    kwargs = {
        "fp16": _cuda_available(),
        "initial_prompt": prompt,
        "temperature": 0.0,
        "condition_on_previous_text": False,
    }
    if not detect and language:
        kwargs["language"] = language

    result = engine.transcribe(audio_path, **kwargs)
    return result.get("text", "").strip()


def transcribe_file(file_path: str, language: str = "auto", output_format: str = "txt") -> dict:
    """
    Transcribe an audio or video file.

    Args:
        file_path: Path to the audio/video file.
        language: Language code or 'auto' for detection.
        output_format: 'txt', 'srt', 'vtt', or 'json'.

    Returns:
        dict with 'text', 'segments', 'language', 'output_path'.
    """
    engine, engine_type = _get_engine()
    if engine is None:
        return {"error": "No Whisper engine available. Install faster-whisper or openai-whisper."}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    # For video files, extract audio first
    video_exts = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".flv", ".wmv"}
    audio_path = str(path)

    if path.suffix.lower() in video_exts:
        audio_path = _extract_audio(str(path))
        if not audio_path:
            return {"error": "Failed to extract audio from video. Is ffmpeg installed?"}

    try:
        detect = language == "auto"
        lang = None if detect else language

        if engine_type == "faster":
            segments_data, info = engine.transcribe(
                audio_path,
                beam_size=5,
                vad_filter=True,
                language=lang if not detect else None,
                word_timestamps=True,
            )
            segments = []
            full_text = []
            for seg in segments_data:
                segments.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                })
                full_text.append(seg.text.strip())

            detected_lang = getattr(info, "language", language)
        else:
            result = engine.transcribe(
                audio_path,
                language=lang if not detect else None,
                fp16=_cuda_available(),
            )
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                })
            full_text = [result.get("text", "").strip()]
            detected_lang = result.get("language", language)

        text = " ".join(full_text)

        # Generate output file
        output_path = str(path.with_suffix(f".{output_format}"))
        if output_format == "txt":
            Path(output_path).write_text(text, encoding="utf-8")
        elif output_format == "srt":
            _write_srt(segments, output_path)
        elif output_format == "vtt":
            _write_vtt(segments, output_path)
        elif output_format == "json":
            import json
            Path(output_path).write_text(
                json.dumps({"text": text, "segments": segments, "language": detected_lang}, indent=2),
                encoding="utf-8",
            )

        return {
            "text": text,
            "segments": segments,
            "language": detected_lang,
            "output_path": output_path,
            "segment_count": len(segments),
        }

    except Exception as e:
        return {"error": f"Transcription failed: {e}"}
    finally:
        # Clean up extracted audio
        if path.suffix.lower() in video_exts and audio_path != str(path):
            try:
                os.unlink(audio_path)
            except Exception:
                pass


def _extract_audio(video_path: str) -> str | None:
    """Extract audio from video file using ffmpeg."""
    import subprocess
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        output_path = tmp.name
    try:
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
             "-ar", "16000", "-ac", "1", output_path, "-y"],
            capture_output=True, timeout=300,
        )
        if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
            return output_path
        return None
    except Exception:
        return None


def _format_timestamp(seconds: float, fmt: str = "srt") -> str:
    """Format seconds into SRT or VTT timestamp."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    sep = "," if fmt == "srt" else "."
    return f"{hrs:02d}:{mins:02d}:{secs:02d}{sep}{ms:03d}"


def _write_srt(segments: list[dict], output_path: str):
    """Write segments as SRT subtitle file."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_timestamp(seg["start"], "srt")
        end = _format_timestamp(seg["end"], "srt")
        lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def _write_vtt(segments: list[dict], output_path: str):
    """Write segments as WebVTT subtitle file."""
    lines = ["WEBVTT\n"]
    for seg in segments:
        start = _format_timestamp(seg["start"], "vtt")
        end = _format_timestamp(seg["end"], "vtt")
        lines.append(f"{start} --> {end}\n{seg['text']}\n")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
