# voice/assistant.py — JARVIS MK37 Voice Control Coordinator
"""
Main hands-free voice control coordinator for JARVIS MK37.
Integrates Speech Recognition, Wake Word Detection, and ReAct loop execution.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Callable
from router import AgentProfile

logger = logging.getLogger("JARVIS.VoiceAssistant")

# Pre-compiled wake word pattern matching jarvis/javis variants
_WAKE_RE = re.compile(
    r"\b(jarvis|javis|jarves|jarvas|jervis|garvis|charvis|harvis|travis|jarvs|hey\s+jarvis|hey\s+javis|ok\s+jarvis|ok\s+javis|hi\s+jarvis|hi\s+javis|hello\s+jarvis|hello\s+javis|hey\s+br|br)\b",
    re.IGNORECASE,
)
_FUZZY_WAKE_MATCHES = (
    "jarvis", "javis", "hey jarvis", "hey javis", "ok jarvis", "ok javis",
    "hi jarvis", "hi javis", "hello jarvis", "hello javis", "wake up", "hey assistant"
)
_WAKE_STRIP_RE = re.compile(
    r"^(hey\s+jarvis|hey\s+javis|ok\s+jarvis|ok\s+javis|hi\s+jarvis|hi\s+javis|hello\s+jarvis|hello\s+javis|br\s+jarvis|hey\s+br|jarvis|javis|jarves|jarvas|jervis|garvis|charvis|harvis)\b[\s,:\.\!]*",
    re.IGNORECASE,
)


_HAS_SR = False
try:
    import speech_recognition as sr  # type: ignore
    _HAS_SR = True
except ImportError:
    pass

_HAS_WINSOUND = False
try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    pass

try:
    from ui_mark import JarvisUI
except ImportError:
    try:
        from ui import JarvisUI
    except ImportError:
        class JarvisUI:
            def __init__(self):
                self.speaking = False
                self.muted = False
                self._state = "IDLE"
                self.on_text_command = None
                self.mic_energy_level = 0.0

            def write_log(self, msg: str) -> None:
                logger.info(f"[UI] {msg}")

            def set_state(self, state: str) -> None:
                self._state = state

            def update_agent_task(self, task_id: str, desc: str, status: str) -> None:
                pass
from core.bootstrap import build_assistant_runtime
from agent.task_queue import get_queue, TaskPriority
from voice.tts import NeuralTTS
from voice.stt import SounddeviceMicrophone


class BRVoiceAssistant:
    """Hands-free Voice Assistant coordinator for JARVIS MK38."""

    # Class-level barge-in VAD singleton (shared across all instances)
    # Lazy-initialized on first speak() to avoid startup overhead
    _barge_vad = None
    _barge_vad_lock = None

    @classmethod
    def _get_barge_vad(cls):
        """Lazy-load the barge-in SileroVAD singleton (thread-safe)."""
        import threading
        if cls._barge_vad_lock is None:
            cls._barge_vad_lock = threading.Lock()
        with cls._barge_vad_lock:
            if cls._barge_vad is None:
                try:
                    from voice.silero_vad import SileroVAD
                    cls._barge_vad = SileroVAD()
                    logger.info("[BargeIn] SileroVAD singleton loaded")
                except Exception as e:
                    logger.warning("[BargeIn] SileroVAD load failed: %s", e)
        return cls._barge_vad

    def __init__(self, ui: JarvisUI | None = None):
        # ── BUG-001 FIX: self.ui must be set FIRST before any other attribute
        # access, because hotkey manager and other subsystems reference self.ui
        # immediately during __init__. The missing assignment caused:
        # AttributeError: 'BRVoiceAssistant' object has no attribute 'ui'
        self.ui = ui if ui is not None else JarvisUI()

        # Initialize ReAct Orchestrator & Backend Gateway via shared runtime
        try:
            runtime = build_assistant_runtime()
            self.orchestrator = runtime.orchestrator
            self.backends = runtime.backends
        except Exception as e:
            logger.warning("Orchestrator init warning: %s", e)
            self.orchestrator = None
            self.backends = {}

        self._loop = None
        self._current_task: asyncio.Task | None = None   # track running command task
        self._task_lock = threading.Lock()                # serialize task switches
        self._async_task_lock: asyncio.Lock | None = None
        self._vocab_cache = self._load_vocab_cache()
        
        # Load configurable settings
        self.name = os.environ.get("JARVIS_ASSISTANT_NAME", "BR").strip()
        self.wake_word = os.environ.get("JARVIS_WAKE_WORD", "jarvis").strip().lower()
        self._wake_listen_timeout = 2.0       # max seconds to wait for speech start
        self._wake_phrase_limit = 4.0         # ⚡ 4.0s capture window for single-breath wake + command
        self._command_timeout = 5.0           # seconds to wait for command speech
        self._command_phrase_limit = 20.0     # allow long complex multi-sentence commands
        self._ambient_calibration = 0.25      # ⚡ 250ms ultra-fast ambient noise calibration


        # Initialize 500ms rolling audio pre-roll ring buffer
        try:
            from voice.ring_buffer import AudioRingBuffer
            self.ring_buffer = AudioRingBuffer(buffer_duration_ms=500)
        except Exception:
            self.ring_buffer = None

        # Initialize Neural TTS Engine
        self.tts = NeuralTTS(voice_key="default", rate="+0%", pitch="+0Hz")
        
        # Initialize Gemini Live Duplex Voice Engine
        try:
            from voice.gemini_live import GeminiLiveVoiceLoop
            self.gemini_live = GeminiLiveVoiceLoop(assistant_ref=self, ui_ref=self.ui)
        except Exception as e:
            logger.warning("Gemini Live loop init warning: %s", e)
            self.gemini_live = None

        # Tracked background tasks (monitor_tasks, etc.) for clean cancellation
        self._bg_tasks: set[asyncio.Task] = set()

        # Initialize Persistent Barge-In Input Stream
        self._persistent_barge_stream = None
        self._persistent_barge_queue = None
        self._barge_in_running = False
        
        barge_in_enabled = os.environ.get("JARVIS_ENABLE_BARGE_IN", "true").lower() in ("1", "true", "yes")
        if barge_in_enabled:
            self._start_persistent_barge_in()

        # Bind manual text command submission and interrupt from UI if available
        if self.ui:
            self.ui.on_text_command = self._on_text_command
            self.ui.on_interrupt = self.stop_speech

        # Start Global Hotkeys System
        try:
            from actions.hotkeys import HotkeyManager
            self.hotkey_manager = HotkeyManager(self)
            self.hotkey_manager.start()
        except Exception as e:
            logger.warning("Hotkeys failed to initialize: %s", e)

    def _load_vocab_cache(self) -> dict:
        """Load vocabulary json cache using project root absolute path."""
        try:
            base_dir = Path(__file__).resolve().parent.parent
            vocab_path = base_dir / "config" / "vocabulary.json"
            if vocab_path.exists():
                data = json.loads(vocab_path.read_text(encoding="utf-8"))
                return data.get("corrections", {})
        except Exception as e:
            logger.warning(f"Vocabulary cache load error: {e}")
        return {}


    def _on_text_command(self, text: str):
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._switch_to_new_command(text), self._loop)

    async def _switch_to_new_command(self, text: str):
        """Cancel any running task/speech, then start the new command with lock synchronization."""
        if self._async_task_lock is None:
            self._async_task_lock = asyncio.Lock()

        async with self._async_task_lock:
            # 1. Stop TTS immediately
            self.tts.stop()
            # 2. Cancel previous async task if still running
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
                try:
                    await self._current_task
                except (asyncio.CancelledError, Exception):
                    pass
            # 3. Launch new command
            self._current_task = asyncio.create_task(self.process_command(text))


    def _start_persistent_barge_in(self):
        """Starts a persistent background RawInputStream to monitor barge-in interuptions."""
        import queue as _q
        self._persistent_barge_queue = _q.Queue()
        self._barge_in_running = True

        def _cb(indata, frames, t, status):
            if self._persistent_barge_queue:
                self._persistent_barge_queue.put(bytes(indata))

        def _run_stream():
            import sounddevice as sd_barge
            import time
            barge_chunk = 512
            while self._barge_in_running:
                try:
                    with sd_barge.RawInputStream(
                        samplerate=16000, channels=1, dtype='int16',
                        blocksize=barge_chunk, callback=_cb
                    ):
                        while self._barge_in_running:
                            # If not speaking, keep queue empty to prevent lag or memory leak
                            if not getattr(self.ui, "speaking", False):
                                try:
                                    while not self._persistent_barge_queue.empty():
                                        self._persistent_barge_queue.get_nowait()
                                except Exception:
                                    pass
                                time.sleep(0.1)

                                continue

                            # We are speaking! Monitor queue for barge-in speech
                            try:
                                pcm = self._persistent_barge_queue.get(timeout=0.08)
                                _barge_vad = self.__class__._get_barge_vad()
                                if _barge_vad:
                                    is_speech, prob, snr_db = _barge_vad.is_speech(pcm)
                                    if is_speech and snr_db > 8.0:
                                        logger.info("[BRG-IN] Barge-in SNR=%.1fdB — stopping TTS", snr_db)
                                        self.tts.stop()
                                        self.ui.speaking = False
                                        self.ui.set_state("LISTENING")
                                        # Clear queue
                                        while not self._persistent_barge_queue.empty():
                                            self._persistent_barge_queue.get_nowait()
                                        time.sleep(0.5)  # Cooldown
                            except Exception:
                                pass
                except Exception as e:
                    logger.debug("Barge-in input stream exception: %s. Retrying...", e)
                    time.sleep(2.0)


        threading.Thread(target=_run_stream, daemon=True, name="PersistentBargeIn").start()

    def speak(self, text: str):
        """Speak text using the neural TTS engine with UI state sync & barge-in support."""
        from voice.tts import clean_for_speech
        log_text = clean_for_speech(text)
        if log_text:
            logger.info(f"[JARVIS] 🗣 Speak: {log_text[:200]}")

        def on_start():
            self.ui.speaking = True
            self.ui.set_state("SPEAKING")

        def on_finish():
            self.ui.speaking = False
            if not self.ui.muted:
                self.ui.set_state("LISTENING")

        self.tts.speak_async(text, on_start=on_start, on_finish=on_finish)

        # ── Barge-In Detection ────────────────────────────────────────────────
        # Clear persistent queue to avoid pre-existing audio triggers
        if getattr(self, "_persistent_barge_queue", None):
            try:
                while not self._persistent_barge_queue.empty():
                    self._persistent_barge_queue.get_nowait()
            except Exception:
                pass


    def stop_speech(self):
        """Halt active neural TTS speech playback immediately for barge-in interruption or user cancel."""
        if hasattr(self, "tts") and self.tts:
            self.tts.stop()
        if hasattr(self, "_current_task") and self._current_task and not self._current_task.done():
            try:
                self._current_task.cancel()
            except Exception:
                pass
        if self.ui:
            self.ui.speaking = False
            if not getattr(self.ui, "muted", False):
                self.ui.set_state("LISTENING")

    def _play_listening_chime(self):
        """Play ascending dual-tone acoustic activation chime when wake word is recognized."""
        try:
            from voice.sound_effects import play_activation_beep
            play_activation_beep()
        except Exception:
            pass

    def _tune_recognizer(self, recognizer):
        """Apply adaptive dynamic energy thresholding and optimal phrase boundary settings."""
        recognizer.dynamic_energy_threshold = True   # Enable adaptive noise floor tracking
        recognizer.dynamic_energy_adjustment_damping = 0.15
        recognizer.dynamic_energy_ratio = 1.35
        recognizer.energy_threshold = max(180, getattr(recognizer, "energy_threshold", 250))  # Enforce 180 RMS floor
        recognizer.pause_threshold = 0.45             # ⚡ Fast 0.45s endpoint pause (slashes latency)
        recognizer.non_speaking_duration = 0.25       # Min non-speech duration before phrase end
        recognizer.phrase_threshold = 0.1           # Min speech length to register

    def _is_wake_phrase(self, text: str) -> bool:
        """Return True when transcript contains explicit wake word ('jarvis', 'javis', 'hey jarvis', or phonetic variants)."""
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()
        if not normalized:
            return False

        if _WAKE_RE.search(normalized):
            return True

        wake_word = self.wake_word.lower().strip()
        if wake_word and wake_word in normalized:
            return True

        return any(target in normalized for target in _FUZZY_WAKE_MATCHES)

    def _extract_command_from_wake(self, text: str) -> str:
        """Extract trailing command when user speaks wake-word and command in a single sentence."""
        if not text:
            return ""
        # Collapse repetitive token loops first
        from voice.prompt_refiner import VoicePromptRefiner
        collapsed = VoicePromptRefiner.get_instance().collapse_repetitions(text)
        norm = collapsed.lower().strip()
        cleaned = _WAKE_STRIP_RE.sub("", norm).strip()

        meaningless = {"hey", "jarvis", "javis", "br", "hello", "hi", "ok", "please"}
        words = set(re.findall(r"\b\w+\b", cleaned.lower()))
        if not cleaned or words.issubset(meaningless) or len(cleaned) <= 2:
            return ""
        return cleaned


    def _get_active_loop(self) -> asyncio.AbstractEventLoop:
        """Safely get the active event loop.

        Inside an async method (which all callers are), asyncio.get_running_loop()
        always succeeds. The old code could mistakenly create a new loop inside an
        already-running loop, which would never be run.
        """
        try:
            # Primary path: we're already inside an async context (always true for callers)
            return asyncio.get_running_loop()
        except RuntimeError:
            # Fallback: called from a non-async context (shouldn't happen in normal usage)
            if self._loop and not self._loop.is_closed():
                return self._loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            return loop

    async def _transcribe_wake(self, audio: sr.AudioData) -> str:
        """⚡ FAST 100% OFFLINE wake-word transcription via local faster-whisper CTranslate2."""
        loop = self._get_active_loop()
        text = ""

        # 1. Ultrafast Specialized Wake-Word Decoder (< 30ms Latency)
        try:
            from voice.whisper_local import transcribe_wake_fast, is_available as whisper_available
            if whisper_available():
                text = await loop.run_in_executor(
                    None, lambda: transcribe_wake_fast(
                        audio.get_wav_data(),
                        language="en",
                        initial_prompt="Jarvis, Javis, Hey Jarvis, Hey Javis"
                    ).lower()
                )
        except Exception:
            text = ""

        # 2. Online Google STT Fallback (Only if offline engine unavailable)
        if not text.strip() and hasattr(self, "r") and self.r:
            try:
                from voice.multilingual import get_google_stt_code
                stt_lang = get_google_stt_code()
                text = await loop.run_in_executor(
                    None, lambda: self.r.recognize_google(audio, language=stt_lang).lower()
                )
            except Exception:
                text = ""

        return text.strip()

    async def _transcribe_command(self, audio: sr.AudioData) -> str:
        """Full-quality command transcription with fallback chain."""
        loop = self._get_active_loop()
        text = ""

        # 0. Try dedicated Gemini Listening API key (if online & configured)
        try:
            from voice.gemini_stt import transcribe_audio_online
            text = await loop.run_in_executor(
                None, lambda: transcribe_audio_online(audio.get_wav_data(), timeout_seconds=4.5)
            )
        except Exception as e:
            text = ""

        # 1. Try local Whisper (100% offline STT fallback or primary when offline)
        if not text:
            try:
                from voice.whisper_local import transcribe as whisper_transcribe, is_available as whisper_available
                from voice.multilingual import get_whisper_code
                if whisper_available():
                    lang_code = get_whisper_code() or "en"
                    prompt = "This is a clear spoken voice command for JARVIS AI assistant to control applications, open web pages, send messages, and execute tasks."
                    text = await loop.run_in_executor(
                        None, lambda: whisper_transcribe(
                            audio.get_wav_data(),
                            language=lang_code,
                            initial_prompt=prompt
                        )
                    )
            except Exception as e:
                logger.warning(f"[Voice] Local Whisper transcription failed: {e}")

        # 2. Try configured default backend (if it has transcribe method)
        if not text and hasattr(self, "backends") and self.backends:
            try:
                default_profile = AgentProfile.GEMINI
                primary = self.backends.get(default_profile)
                if primary and hasattr(primary, "transcribe"):
                    text = await loop.run_in_executor(
                        None, lambda: primary.transcribe(audio.get_wav_data())
                    )
            except Exception as e:
                logger.warning(f"Primary transcription chain failed: {e}")

        return text


    async def process_command(self, text: str):
        if not text or not text.strip():
            return

        # Refine raw acoustic speech transcript into a clean execution prompt
        from voice.prompt_refiner import refine_voice_prompt
        ref_res = refine_voice_prompt(text)
        text_clean = ref_res["refined"]

        if not text_clean or not text_clean.strip():
            raw_preview = ref_res.get("raw", text)[:60]
            self.ui.write_log(f"SYS: Ignored wake/noise artifact: \"{raw_preview}\"")
            self.ui.set_state("LISTENING")
            return

        if ref_res["was_modified"]:
            self.ui.write_log(f"🎙️ Spoken Raw: \"{ref_res['raw']}\"")
            self.ui.write_log(f"✨ Refined Prompt: \"{text_clean}\"")
        else:
            self.ui.write_log(f"You: {text_clean}")

        low = text_clean.lower().strip()

        # Handle Total Recall voice capture: "remember that..." or "remember..."
        if low.startswith("remember that ") or low.startswith("remember "):
            self.ui.write_log(f"🧠 Total Recall Capture: \"{text_clean}\"")
            try:
                port = int(os.environ.get("PORT", "8000"))
                def _post_remember():
                    import urllib.request
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{port}/api/remember",
                        data=json.dumps({"text": text_clean}).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return response.status, json.loads(response.read().decode("utf-8"))

                status_code, data = await asyncio.to_thread(_post_remember)
                if status_code == 200:
                    confirm = data.get("confirmation", "Recorded to your brain, sir.")
                    self.speak(confirm)
                    self.ui.set_state("IDLE")
                    return
            except Exception as e:
                self.ui.write_log(f"SYS: Capture sync error: {e}")


        # System shutdown ONLY triggers on exact standalone shutdown commands
        exact_shutdown_commands = {
            "exit", "quit", "goodbye", "shutdown", "bye",
            "shutdown jarvis", "exit jarvis", "close jarvis", "stop jarvis",
            "shutdown br", "exit br", "stop br"
        }

        if low in exact_shutdown_commands:
            self.ui.write_log("SYS: Shutting down.")
            self.speak("Goodbye, sir.")
            await asyncio.sleep(2.5)
            if self._loop and self._loop.is_running():
                self._loop.stop()
            sys.exit(0)

        # Detect multiple parallel goals
        parallel_keywords = ["while also", "at the same time", "simultaneously", "and also"]
        
        # Don't treat | in markdown tables as goal separators
        is_table = False
        if "|" in text_clean:
            for line in text_clean.splitlines():
                line_s = line.strip()
                if (line_s.startswith("|") and line_s.endswith("|") and len(line_s) > 1) or "|---" in line_s or "--|" in line_s:
                    is_table = True
                    break
        
        is_parallel = ("|" in text_clean and not is_table) or any(kw in low for kw in parallel_keywords)

        if is_parallel:
            goals = []
            if "|" in text_clean:
                goals = [g.strip() for g in text_clean.split("|") if g.strip()]
            else:
                split_word = next((kw for kw in parallel_keywords if kw in low), "and also")
                pattern = re.compile(re.escape(split_word), re.IGNORECASE)
                goals = [g.strip() for g in pattern.split(text_clean) if g.strip()]

            if len(goals) > 1:
                self.ui.write_log(f"SYS: Running {len(goals)} tasks in parallel...")
                self.speak("Executing multiple tasks in parallel.")

                q = get_queue()
                task_ids = q.submit_many(goals, priority=TaskPriority.NORMAL, speak=self.speak)

                for idx, tid in enumerate(task_ids):
                    self.ui.update_agent_task(tid, goals[idx][:20], "running")

                async def monitor_tasks():
                    while True:
                        all_done = True
                        for tid in task_ids:
                            status = q.get_status(tid)
                            if status and status["status"] not in ("completed", "failed", "cancelled"):
                                all_done = False
                            elif status and status["status"] == "completed":
                                self.ui.update_agent_task(tid, goals[task_ids.index(tid)][:20], "completed")
                            elif status and status["status"] == "failed":
                                self.ui.update_agent_task(tid, goals[task_ids.index(tid)][:20], "failed")
                        if all_done:
                            break
                        await asyncio.sleep(0.5)
                    self.speak("All parallel tasks completed.")
                    self.ui.set_state("LISTENING")

                asyncio.create_task(monitor_tasks())
                # FLAW-4 FIX: track the monitor task so it can be cancelled on shutdown
                _mt = asyncio.create_task(monitor_tasks())
                self._bg_tasks.add(_mt)
                _mt.add_done_callback(self._bg_tasks.discard)
                return

        # Single goal execution using ReAct Orchestrator loop
        try:
            response = await asyncio.to_thread(self.orchestrator.chat, text_clean)
            # Check if this task was cancelled during the blocking chat() call
            if asyncio.current_task() and asyncio.current_task().cancelled():
                return
            if not response or not str(response).strip():
                response = "I am ready, sir. Please specify a single task or command."

            # Check for structured diagnostic failure
            if "TASK_EXECUTION_FAILED" in response or "All backends failed" in response:
                logger.error("[Voice] STT_SUCCESS_BACKEND_FAILURE encountered for prompt: %s", text_clean[:80])
                self.ui.write_log("SYS: [STT_SUCCESS_BACKEND_FAILURE] AI execution failed — diagnostic trace generated.")

                # Extract user-friendly portion if present
                if "[BR JARVIS:" in response and "]" in response:
                    user_part = response.split("[BR JARVIS:")[-1].split("]")[0].strip()
                    spoken_summary = f"I couldn't complete the planning stage because all compatible AI providers failed. {user_part}"
                else:
                    spoken_summary = "I was unable to complete the AI planning stage because all compatible model providers failed. Please check connectivity or proxy status."
                
                self.ui.write_log(f"JARVIS: {response[:500]}")
                self.speak(spoken_summary)
                self.ui.set_state("LISTENING")
                return

            # Log clean version to UI
            from voice.tts import clean_for_speech, summarize_for_speech
            clean_log = clean_for_speech(response)
            self.ui.write_log(f"JARVIS: {clean_log[:500] if clean_log else response[:500]}")
            spoken_summary = summarize_for_speech(response, max_chars=600)
            if not spoken_summary or not spoken_summary.strip():
                spoken_summary = "I have executed all requested operations and saved the output to your workspace, sir."
            self.speak(spoken_summary)
        except asyncio.CancelledError:
            # Task was cancelled by a new incoming command — silently exit
            return
        except Exception as e:
            err_msg = f"Error processing request: {e}"
            self.ui.write_log(f"ERR: {err_msg}")
            self.speak("Sorry, I encountered an error processing that request.")
            traceback.print_exc()

        self.ui.set_state("LISTENING")

    async def run(self):
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        # Initialize AI core backends if not already initialized in __init__
        if not self.orchestrator:
            if self.ui:
                self.ui.set_state("THINKING")
                self.ui.write_log("SYS: Initializing AI backends...")
            runtime = build_assistant_runtime()
            self.orchestrator = runtime.orchestrator
            self.backends = runtime.backends
        if self.ui:
            self.ui.write_log("SYS: JARVIS Cognitive Core online.")

        # Background thread: sync TTS speaking state with UI animation (thread-safe)
        def animation_sync_loop():
            while True:
                try:
                    is_speaking = getattr(self.tts, "is_speaking", getattr(self.tts, "_is_speaking", False))
                    if callable(is_speaking):
                        is_speaking = is_speaking()
                    if self.ui:
                        self.ui.speaking = bool(is_speaking)
                        ui_state = getattr(self.ui, "_state", "IDLE")
                        if is_speaking:
                            if ui_state != "SPEAKING":
                                self.ui.set_state("SPEAKING")
                        elif ui_state == "SPEAKING":
                            self.ui.set_state("LISTENING")
                except Exception:
                    pass
                time.sleep(0.05)


        # Setup Speech Recognition
        mic_available = False
        self.r = None
        mic = None

        if _HAS_SR:
            try:
                self.r = sr.Recognizer()
                mic = SounddeviceMicrophone()
                self._tune_recognizer(self.r)
                mic_available = True
            except Exception as e:
                self.ui.write_log(f"WRN: Hands-free mic offline: {e}")
        else:
            self.ui.write_log("WRN: speech_recognition not installed. Text-only mode.")

        threading.Thread(target=animation_sync_loop, daemon=True).start()

        self.ui.set_state("LISTENING")
        self.speak(f"{self.name} online. Neural core active. Awaiting your command.")

        # Execute custom startup commands
        try:
            from actions.custom_commands import custom_command_engine
            if custom_command_engine.startup_commands:
                self.ui.write_log("SYS: Executing startup commands...")
                for startup_cmd in custom_command_engine.startup_commands:
                    # Run startup command asynchronously
                    self._loop.call_soon_threadsafe(
                        lambda c=startup_cmd: custom_command_engine.execute({"actions": [c]}, {}, speak_callback=self.speak)
                    )
        except Exception as e:
            logger.warning(f"[Voice] Startup commands error: {e}")

        if not mic_available or not self.r or not mic:
            self.ui.write_log("SYS: Keyboard text control operational.")
            while True:
                await asyncio.sleep(1.0)

        # Open and start microphone stream globally (one-time setup)
        try:
            with mic as source:
                self.ui.write_log("SYS: Calibrating microphone noise threshold...")
                try:
                    self.r.adjust_for_ambient_noise(source, duration=self._ambient_calibration)
                    if self.r.energy_threshold < 180:
                        self.r.energy_threshold = 180
                    self.r.phrase_threshold = 0.08
                    self.r.dynamic_energy_ratio = 1.25
                    mic.drain()  # ⚡ instant flush instead of sleep + manual loop

                    # ── AdaptiveNoiseCalibrator: tune VAD threshold to environment ──
                    try:
                        from voice.noise_calibrator import get_calibrator
                        _nc = get_calibrator()
                        if not _nc.is_calibrated:
                            _nc.start_background_calibration(
                                chunk_size=512, sample_rate=16000
                            )
                        # Feed noise floor into STT energy pre-filter
                        if hasattr(mic, 'set_noise_floor') and _nc.is_calibrated:
                            mic.set_noise_floor(_nc.baseline_rms)
                        logger.info("[Voice] NoiseCalibrator: %r", _nc)
                    except Exception as _nc_err:
                        logger.debug("NoiseCalibrator boot error: %s", _nc_err)

                    self.ui.set_state("LISTENING")
                    self.ui.write_log(f"SYS: Microphone active (Device {mic.device_index}). Hands-free mode active. Listening for 'Jarvis' or 'Hey Jarvis'...")

                    # ── Mic Health Watchdog ────────────────────────────────────────
                    def _mic_watchdog():
                        while True:
                            time.sleep(5.0)

                            try:
                                if not mic.is_alive():
                                    logger.warning("[Watchdog] Mic stale — attempting hot-plug recovery")
                                    self.ui.write_log("WRN: Mic disconnect detected. Reconnecting...")
                                    if mic.try_reconnect():
                                        # Feed updated noise floor after recovery
                                        try:
                                            from voice.noise_calibrator import get_calibrator
                                            _nc2 = get_calibrator()
                                            if hasattr(mic, 'set_noise_floor'):
                                                mic.set_noise_floor(_nc2.baseline_rms)
                                        except Exception:
                                            pass
                                        self.ui.write_log("SYS: Mic recovered successfully.")
                                    else:
                                        self.ui.write_log("ERR: Mic recovery failed. Using text input only.")
                            except Exception:
                                pass

                    threading.Thread(target=_mic_watchdog, daemon=True, name="MicWatchdog").start()


                except Exception as e:
                    self.ui.write_log(f"ERR: Microphone calibration failed: {e}")


                # Wake-word passive listening loop
                while True:
                    try:
                        # Passive listening checks: suspend listening while speaking, thinking, executing, or muted
                        if self.ui.speaking or self.ui._state in ("THINKING", "SPEAKING", "EXECUTING", "BUSY") or getattr(self.ui, "muted", False):
                            await asyncio.sleep(0.1)
                            continue

                        # ⚡ Dynamic micro-endpoint tuning for ultra-snappy wake detection
                        self.r.pause_threshold = 0.25
                        self.r.non_speaking_duration = 0.15

                        # Drain microphone buffer so old frames recorded while speaking/thinking/executing are flushed
                        try:
                            await asyncio.sleep(0.15)
                            mic.drain()
                        except Exception:
                            pass

                        # ⚡ Listen for wake phrase (4.0s limit captures single-breath wake+command)
                        audio = await self._loop.run_in_executor(
                            None, lambda: self.r.listen(
                                source,
                                timeout=self._wake_listen_timeout,
                                phrase_time_limit=self._wake_phrase_limit,
                            )
                        )



                        # ⚡ ULTRAFAST wake decoding
                        text = await self._transcribe_wake(audio)

                        if self._is_wake_phrase(text):
                            # Instant audio feedback & listening HUD trigger
                            self._play_listening_chime()
                            self.ui.set_state("LISTENING")
                            self.ui.write_log("SYS: 🎙️ Wake word detected. Active listening mode...")

                            # Check if command was spoken in the same sentence as the wake word
                            embedded_cmd = self._extract_command_from_wake(text)
                            if embedded_cmd:
                                self.ui.write_log(f"SYS: Command captured: '{embedded_cmd}'")
                                await self._switch_to_new_command(embedded_cmd)
                                continue

                            # Drain microphone buffer so chime echo is not recorded as voice input
                            try:
                                mic.drain()
                            except Exception:
                                pass

                            # Restore full command listening thresholds for active command capture
                            # ── Dynamic Pause Threshold ──────────────────────────────────────────
                            # Use adaptive pause based on environment noise level.
                            # QUIET env → tighter 0.55s, NOISY env → looser 0.90s
                            try:
                                from voice.noise_calibrator import get_calibrator
                                _env = get_calibrator().environment_label
                                _pause = {"QUIET": 0.55, "MODERATE": 0.70, "NOISY": 0.90}.get(_env, 0.70)
                            except Exception:
                                _pause = 0.70
                            self.r.pause_threshold = _pause
                            self.r.non_speaking_duration = max(0.20, _pause * 0.40)


                            # Listen for follow-up command if user spoke only the wake word
                            try:
                                audio_cmd = await self._loop.run_in_executor(
                                    None, lambda: self.r.listen(
                                        source,
                                        timeout=self._command_timeout,
                                        phrase_time_limit=self._command_phrase_limit
                                    )
                                )
                                # Play deep processing bass chime when voice capture finishes
                                try:
                                    from voice.sound_effects import play_processing_bass_chime
                                    play_processing_bass_chime()
                                except Exception:
                                    pass

                                # Full-quality transcription for command
                                cmd_text = await self._transcribe_command(audio_cmd)

                                if cmd_text.strip():
                                    await self._switch_to_new_command(cmd_text)
                                else:
                                    self.ui.write_log("SYS: No command detected. Resuming...")
                                    self.ui.set_state("LISTENING")
                            except sr.WaitTimeoutError:
                                self.ui.write_log("SYS: Command capture timed out — no input heard.")
                                try:
                                    mic.drain()
                                except Exception:
                                    pass
                                self.ui.set_state("LISTENING")

                    except sr.WaitTimeoutError:
                        # Expected timeout when silence, continue loop immediately
                        pass
                    except RuntimeError as e:
                        if "shutdown" in str(e).lower() or "closed" in str(e).lower():
                            break
                        logger.warning(f"[Voice Loop Error]: {e}")
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        logger.warning(f"[Voice Loop Error]: {e}")
                        await asyncio.sleep(0.3)

        except Exception as e:
            self.ui.write_log(f"ERR: Failed to start microphone stream: {e}")
            self.ui.write_log("SYS: Keyboard text control operational.")
            while True:
                await asyncio.sleep(1.0)


_global_voice_assistant: Optional[BRVoiceAssistant] = None
_voice_assistant_lock = threading.Lock()


def get_voice_assistant(ui_instance: Optional[Any] = None) -> BRVoiceAssistant:
    """Return the global BRVoiceAssistant singleton (thread-safe)."""
    global _global_voice_assistant
    if _global_voice_assistant is not None:
        return _global_voice_assistant
    with _voice_assistant_lock:
        if _global_voice_assistant is None:
            _global_voice_assistant = BRVoiceAssistant(ui=ui_instance)
    return _global_voice_assistant

