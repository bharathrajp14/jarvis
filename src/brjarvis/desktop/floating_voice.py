"""Voice-to-text and short speaker services for the BR JARVIS floating dock."""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class FloatingVoiceController:
    """One-shot push-to-talk controller with injectable capture/transcription seams."""

    def __init__(
        self,
        *,
        microphone_factory: Optional[Callable[[], Any]] = None,
        transcriber: Optional[Callable[[bytes], str]] = None,
        timeout: float = 2.0,
        phrase_time_limit: float = 12.0,
    ) -> None:

        self._microphone_factory = microphone_factory or self._default_microphone
        self._transcriber = transcriber or self._default_transcriber
        self._timeout = timeout
        self._phrase_time_limit = phrase_time_limit
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._recording = False
        self._active_source: Any = None
        self._generation = 0

    @property
    def available(self) -> bool:
        try:
            import speech_recognition  # noqa: F401
            import sounddevice  # noqa: F401

            return True
        except ImportError:
            return False

    @property
    def recording(self) -> bool:
        with self._lock:
            return self._recording

    def start(
        self,
        *,
        on_state: Optional[Callable[[str, str], None]] = None,
        on_transcript: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> bool:
        with self._lock:
            if self._recording:
                self.stop()
                return False
            self._recording = True
            self._generation += 1
            generation = self._generation
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._capture,
                args=(generation, on_state, on_transcript, on_error),
                daemon=True,
                name="floating-voice-capture",
            )
            self._thread.start()
        return True

    def stop(self) -> None:
        with self._lock:
            self._generation += 1
            self._recording = False
        self._stop_event.set()
        source = self._active_source
        if source is not None:
            try:
                source.__exit__(None, None, None)
            except Exception:
                pass

    def _capture(self, generation, on_state, on_transcript, on_error) -> None:
        def current() -> bool:
            with self._lock:
                return generation == self._generation and self._recording

        try:
            self._emit(on_state, "recording", "Listening…")
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            source = self._microphone_factory()
            self._active_source = source
            with source:
                if self._stop_event.is_set():
                    return
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.15)
                except Exception:
                    pass
                audio = recognizer.listen(source, timeout=self._timeout, phrase_time_limit=self._phrase_time_limit)

            if self._stop_event.is_set() or not current():
                return
            self._emit(on_state, "transcribing", "Transcribing…")
            wav_bytes = audio.get_wav_data()
            transcript = str(self._transcriber(wav_bytes) or "").strip()
            if not transcript:
                try:
                    transcript = str(recognizer.recognize_google(audio) or "").strip()
                except Exception:
                    transcript = ""
            if not current():
                return
            if transcript:
                if on_transcript:
                    on_transcript(transcript)
                self._emit(on_state, "ready", "Voice transcript ready")
            else:
                self._emit(on_state, "error", "No speech detected")
        except Exception as exc:  # noqa: BLE001 - convert hardware/provider errors to UI state
            logger.info("Floating voice capture unavailable: %s", exc)
            if current():
                if on_error:
                    on_error(self._safe_error(exc))
                self._emit(on_state, "error", self._safe_error(exc))
        finally:
            self._active_source = None
            with self._lock:
                if generation == self._generation:
                    self._recording = False

    @staticmethod
    def _default_microphone():
        from brjarvis.voice.stt import SounddeviceMicrophone

        return SounddeviceMicrophone()

    @staticmethod
    def _default_transcriber(wav_bytes: bytes) -> str:
        from brjarvis.voice.whisper_local import transcribe

        return transcribe(wav_bytes, language="en")

    @staticmethod
    def _emit(callback, state: str, message: str) -> None:
        if callback:
            callback(state, message)

    @staticmethod
    def _safe_error(exc: BaseException) -> str:
        text = str(exc).strip() or exc.__class__.__name__
        lowered = text.lower()
        if "waittimeout" in lowered or "timed out" in lowered or "timeout" in lowered:
            return "Listening timed out. Click MIC to try again."
        if "microphone" in lowered or "input" in lowered or "audio" in lowered:
            return "No microphone is available. Check the Windows input device and retry."
        return text[:240]


class FloatingSpeakerController:
    """Lazy NeuralTTS wrapper for short, cleaned, on-demand response playback."""

    def __init__(self, tts_factory: Optional[Callable[[], Any]] = None) -> None:
        self._tts_factory = tts_factory or self._default_tts
        self._tts = None
        self._lock = threading.RLock()
        self._last_text = ""
        self._speaking = False

    @property
    def available(self) -> bool:
        return self._tts is not None or self._tts_factory is not None

    @property
    def speaking(self) -> bool:
        with self._lock:
            if self._tts is not None and getattr(self._tts, "is_speaking", False):
                return True
            return self._speaking

    def speak(
        self,
        text: str,
        *,
        on_state: Optional[Callable[[str, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> bool:
        from brjarvis.voice.tts import summarize_for_speech

        short_text = summarize_for_speech(text or "", max_chars=600)
        if not short_text:
            if on_error:
                on_error("There is no response to speak yet.")
            return False
        with self._lock:
            if self._tts is None:
                self._tts = self._tts_factory()
            self._last_text = short_text
            self._speaking = True
            tts = self._tts
        self._emit(on_state, "synthesizing", "Preparing short response…")

        def on_start():
            self._emit(on_state, "speaking", "Speaking…")

        def on_finish():
            with self._lock:
                self._speaking = False
            self._emit(on_state, "ready", "Response ready")

        try:
            tts.speak_async(short_text, on_start=on_start, on_finish=on_finish)
            return True
        except Exception as exc:  # noqa: BLE001 - convert audio errors to UI state
            with self._lock:
                self._speaking = False
            logger.info("Floating speaker failed: %s", exc)
            if on_error:
                on_error(self._safe_error(exc))
            return False

    def stop(self) -> None:
        with self._lock:
            tts = self._tts
            self._speaking = False
        if tts is not None and hasattr(tts, "stop"):
            tts.stop()

    def replay(self, *, on_state=None, on_error=None) -> bool:
        return self.speak(self._last_text, on_state=on_state, on_error=on_error)

    @staticmethod
    def _default_tts():
        from brjarvis.voice.tts import NeuralTTS

        return NeuralTTS()

    @staticmethod
    def _emit(callback, state: str, message: str) -> None:
        if callback:
            callback(state, message)

    @staticmethod
    def _safe_error(exc: BaseException) -> str:
        text = str(exc).strip() or exc.__class__.__name__
        return text[:240]
