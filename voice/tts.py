# voice/tts.py — Upgraded Parallel Pipelined TTS Architecture for JARVIS MK37
"""
Sentence-level pipelined streaming TTS engine with zero sentence pauses,
instant <200ms audio startup, parallel pre-fetching, and HD Windows OneCore Female Natural Voice.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time
import uuid
import queue
import shutil
import tempfile
import threading
import subprocess
import traceback
from pathlib import Path

logger = logging.getLogger("JARVIS.TTS")


try:
    import pythoncom
    _HAS_PYTHONCOM = True
except ImportError:
    _HAS_PYTHONCOM = False

_OS = "Windows" if sys.platform == "win32" else ("Darwin" if sys.platform == "darwin" else "Linux")

try:
    import edge_tts
    _HAS_EDGE_TTS = True
except ImportError:
    _HAS_EDGE_TTS = False


def resolve_output_device() -> int | str | None:
    out_dev = os.environ.get("JARVIS_AUDIO_OUTPUT_DEVICE", "").strip()
    if not out_dev:
        return None
    if out_dev.isdigit():
        return int(out_dev)
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            if dev.get("max_output_channels", 0) > 0 and out_dev.lower() in dev.get("name", "").lower():
                return idx
    except Exception:
        pass
    return out_dev


def _is_bing_reachable(timeout: float = 0.4) -> bool:
    """Fast socket probe to check if Microsoft Bing Edge-TTS endpoint is reachable."""
    import socket
    try:
        sock = socket.create_connection(("speech.platform.bing.com", 443), timeout=timeout)
        sock.close()
        return True
    except Exception:
        return False


class MCIPlayer:
    """Play MP3/WAV files using sounddevice, Windows MCI, or system audio utilities."""
    _winmm = None
    _lock = threading.Lock()
    _active_processes: dict[str, subprocess.Popen] = {}
    _sd_finish_time: float = 0.0

    @classmethod
    def _init_winmm(cls):
        if cls._winmm is None and _OS == "Windows":
            import ctypes
            cls._winmm = ctypes.windll.winmm

    @classmethod
    def play_file(cls, filepath: str) -> str:
        alias = f"jarvis_tts_{uuid.uuid4().hex[:8]}"
        filepath_str = str(Path(filepath).resolve())

        # Try sounddevice + soundfile first for ultra-low latency
        try:
            import soundfile as sf
            import sounddevice as sd
            data, fs = sf.read(filepath_str, dtype="float32")
            out_dev = resolve_output_device()
            sd.play(data, fs, device=out_dev)
            cls._sd_finish_time = time.time() + (len(data) / float(fs))
            return alias
        except Exception:
            pass

        if _OS == "Windows":
            cls._init_winmm()
            if cls._winmm:
                cmd_open = f'open "{filepath_str}" type mpegvideo alias {alias}'
                cls._winmm.mciSendStringW(cmd_open, None, 0, 0)
                cmd_play = f'play {alias}'
                cls._winmm.mciSendStringW(cmd_play, None, 0, 0)
                return alias

        if _OS == "Darwin":
            proc = subprocess.Popen(["afplay", filepath_str], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with cls._lock:
                cls._active_processes[alias] = proc
            return alias

        for player in ["ffplay", "mpv", "cvlc", "aplay"]:
            if shutil.which(player):
                cmd = [player, "-nodisp", "-autoexit", filepath_str] if player == "ffplay" else ([player, "--no-terminal", filepath_str] if player == "mpv" else [player, filepath_str])
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with cls._lock:
                    cls._active_processes[alias] = proc
                return alias

        return alias

    @classmethod
    def is_playing(cls, alias: str) -> bool:
        if time.time() < cls._sd_finish_time:
            return True

        try:
            import sounddevice as sd
            if sd.get_stream() and sd.get_stream().active:
                return True
        except Exception:
            pass

        if _OS == "Windows":
            cls._init_winmm()
            if cls._winmm:
                import ctypes
                buf = ctypes.create_unicode_buffer(128)
                cls._winmm.mciSendStringW(f"status {alias} mode", buf, 128, 0)
                return buf.value.strip().lower() == "playing"

        with cls._lock:
            proc = cls._active_processes.get(alias)
            if proc:
                return proc.poll() is None

        return False

    @classmethod
    def stop(cls, alias: str):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

        if _OS == "Windows":
            cls._init_winmm()
            if cls._winmm:
                cls._winmm.mciSendStringW(f"stop {alias}", None, 0, 0)
                cls._winmm.mciSendStringW(f"close {alias}", None, 0, 0)
        else:
            with cls._lock:
                proc = cls._active_processes.pop(alias, None)
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                    except Exception:
                        pass

    @classmethod
    def stop_all(cls):
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

        if _OS == "Windows":
            cls._init_winmm()
            if cls._winmm:
                cls._winmm.mciSendStringW("close all", None, 0, 0)
        else:
            with cls._lock:
                for alias, proc in list(cls._active_processes.items()):
                    if proc and proc.poll() is None:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                cls._active_processes.clear()


def clean_for_speech(text: str) -> str:
    """Clean text for natural, fluid spoken audio output."""
    if not text:
        return ""

    raw_check = text.strip()
    if (
        raw_check.startswith("[Executed Tool:")
        or raw_check.startswith("Executed Tool")
        or "import os" in text
        or "os.walk" in text
        or "open(filepath" in text
    ):
        return "I have executed the requested operations, sir."

    def _path_to_basename(match):
        full_path = match.group(0)
        parts = [p.strip() for p in re.split(r"[\\/]", full_path) if p.strip()]
        if len(parts) >= 2:
            return f" {parts[-2]} folder, {parts[-1]} "
        elif parts:
            return f" {parts[-1]} "
        return " the file "

    text = re.sub(r"```[\s\S]*?```", " Code snippet omitted for brevity. ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[A-Za-z]:\\[^:\n\r\t\s]+", _path_to_basename, text)
    text = re.sub(r"\bworkspace[\\/][A-Za-z0-9_\-.]+", _path_to_basename, text)
    text = re.sub(r"/[\w.-]+(?:/[\w.-]+)+", "", text)
    text = re.sub(r"[\#\*\_\~\>\[\]\(\)\{\}\\\|\+\=\-\#]", " ", text)
    text = re.sub(r"[^\w\s\.,!\?'\"]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_sentences(text: str) -> list[str]:
    """Split clean text into natural speech sentences."""
    if not text:
        return []
    raw = re.split(r"(?<=[.!?])\s+", text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) > 1:
            sentences.append(s)
    return sentences if sentences else ([text.strip()] if text.strip() else [])


def summarize_for_speech(text: str, max_chars: int = 600) -> str:
    """Summarize and clean long AI output for natural spoken audio."""
    raw_check = (text or "").strip()
    if (
        raw_check.startswith("[Executed Tool:")
        or raw_check.startswith("Executed Tool")
        or "import os" in text
        or "os.walk" in text
    ):
        return "I have executed the requested operations, sir."

    clean = clean_for_speech(text)
    if not clean:
        return ""
    if len(clean) <= max_chars:
        return clean

    truncated = clean[:max_chars]
    last_punct = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if last_punct > 100:
        return truncated[:last_punct + 1]
    return truncated.strip() + "..."


class NeuralTTS:
    """High-quality pipelined text-to-speech engine with zero sentence gap and instant audio startup."""

    VOICES = {
        "default":   "en-US-AriaNeural",       # Soft, ultra-natural, warm neural female voice
        "female_us": "en-US-JennyNeural",      # Warm American female
        "female_gb": "en-GB-SoniaNeural",      # Elegant British female
        "male_us":   "en-US-GuyNeural",         # American male
    }

    def __init__(self, voice_key: str = "default", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = self.VOICES.get(voice_key, self.VOICES["default"])
        self.rate = rate
        self.pitch = pitch
        self._temp_dir = Path(tempfile.gettempdir()) / "br_tts_cache"
        self._temp_dir.mkdir(exist_ok=True)
        self._current_alias = None
        self._is_speaking = False
        self._cancel_event = threading.Event()   # instant cancel signal
        self._generation_id = 0                  # monotonic generation counter for task isolation
        self._gen_lock = threading.Lock()         # thread lock for generation ID
        self._last_edge_check = 0.0              # timestamp of last DNS socket check
        self._edge_cooldown_until = 0.0          # cooldown timestamp when Edge-TTS fails
        threading.Thread(target=self._prune_cache, daemon=True).start()
        self._init_fallback_speaker()


    def _init_fallback_speaker(self):
        """Always initialize local fallback speaker for robust runtime recovery."""
        self._sapi_speaker = None
        if _OS == "Windows":
            self._init_sapi5()
        else:
            self._init_linux_tts()

    def _prune_cache(self, max_files: int = 500, max_bytes: int = 200 * 1024 * 1024):
        """Prune TTS cache directory if it exceeds max files or total byte limit."""
        try:
            files = sorted(self._temp_dir.glob("tts_*.mp3"), key=lambda p: p.stat().st_mtime)
            total_size = sum(p.stat().st_size for p in files)
            while files and (len(files) > max_files or total_size > max_bytes):
                oldest = files.pop(0)
                try:
                    total_size -= oldest.stat().st_size
                    oldest.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass

    def _init_sapi5(self):
        """Initialize high-quality SAPI5 / Windows OneCore Natural Neural voice offline."""
        try:
            if _HAS_PYTHONCOM:
                pythoncom.CoInitialize()
            import win32com.client
            self._sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
            
            # Try loading HD Windows Speech_OneCore Natural Voices
            onecore_loaded = False
            try:
                cat = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
                cat.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices", False)
                tokens = cat.EnumerateTokens()
                if tokens.Count > 0:
                    female_names = ("Susan", "Hazel", "Sonia", "Jenny", "Aria", "Eva", "Zira")
                    for fname in female_names:
                        for i in range(tokens.Count):
                            desc = tokens.Item(i).GetDescription()
                            if fname.lower() in desc.lower():
                                self._sapi_speaker.Voice = tokens.Item(i)
                                onecore_loaded = True
                                if 'logger' in globals() or 'logger' in locals():
                                    logger.info(f"{ f"[JARVIS] ✅ HD Offline Female Natural Voice loaded: '{desc}'" }" if isinstance(f"[JARVIS] ✅ HD Offline Female Natural Voice loaded: '{desc}'", str) else f"[JARVIS] ✅ HD Offline Female Natural Voice loaded: '{desc}'")
                                else:
                                    import logging
                                    logging.getLogger(__name__).info(f"{ f"[JARVIS] ✅ HD Offline Female Natural Voice loaded: '{desc}'" }" if isinstance(f"[JARVIS] ✅ HD Offline Female Natural Voice loaded: '{desc}'", str) else f"[JARVIS] ✅ HD Offline Female Natural Voice loaded: '{desc}'")
                                break
                        if onecore_loaded:
                            break

                    if not onecore_loaded:
                        self._sapi_speaker.Voice = tokens.Item(0)
                        onecore_loaded = True
                        if 'logger' in globals() or 'logger' in locals():
                            logger.info(f"{ f"[JARVIS] ✅ HD Offline Natural Voice loaded: '{tokens.Item(0).GetDescription()}'" }" if isinstance(f"[JARVIS] ✅ HD Offline Natural Voice loaded: '{tokens.Item(0).GetDescription()}'", str) else f"[JARVIS] ✅ HD Offline Natural Voice loaded: '{tokens.Item(0).GetDescription()}'")
                        else:
                            import logging
                            logging.getLogger(__name__).info(f"{ f"[JARVIS] ✅ HD Offline Natural Voice loaded: '{tokens.Item(0).GetDescription()}'" }" if isinstance(f"[JARVIS] ✅ HD Offline Natural Voice loaded: '{tokens.Item(0).GetDescription()}'", str) else f"[JARVIS] ✅ HD Offline Natural Voice loaded: '{tokens.Item(0).GetDescription()}'")
            except Exception:
                pass

            if not onecore_loaded:
                voices = self._sapi_speaker.GetVoices()
                for fname in ("Zira", "Hazel", "Eva", "Susan"):
                    for i in range(voices.Count):
                        desc = voices.Item(i).GetDescription()
                        if fname.lower() in desc.lower():
                            self._sapi_speaker.Voice = voices.Item(i)
                            onecore_loaded = True
                            logger.info(f"✅ SAPI5 Female Voice loaded: '{desc}'")
                            break
                    if onecore_loaded:
                        break

            self._sapi_speaker.Rate = 2
        except Exception as e:
            logger.warning(f"SAPI5 fallback failed: {e}")
            self._sapi_speaker = None


    def _init_linux_tts(self):
        """Initialize Linux speech dispatcher or espeak fallback."""
        if shutil.which("spd-say") or shutil.which("espeak") or shutil.which("espeak-ng"):
            if 'logger' in globals() or 'logger' in locals():
                logger.info("[JARVIS] Linux native CLI TTS engine ready.")
            else:
                import logging
                logging.getLogger(__name__).info("[JARVIS] Linux native CLI TTS engine ready.")

    def stop(self):
        """Instantly stop all active speech output and cancel pre-fetched queues."""
        with self._gen_lock:
            self._generation_id += 1
            self._cancel_event.set()

        if self._current_alias:
            MCIPlayer.stop(self._current_alias)
            self._current_alias = None

        if _OS == "Windows" and self._sapi_speaker:
            try:
                self._sapi_speaker.Speak("", 2)
            except Exception:
                pass

        self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        """Returns True if speech output is currently playing."""
        return getattr(self, "_is_speaking", False)

    def speak_async(self, text: str, on_start=None, on_finish=None):
        """Async non-blocking pipelined pre-fetching speech interface."""
        if not text or not text.strip():
            if on_finish:
                on_finish()
            return

        self.stop()

        with self._gen_lock:
            self._cancel_event.clear()
            gen_id = self._generation_id

        thread = threading.Thread(
            target=self._speak_streaming_worker,
            args=(text, on_start, on_finish, gen_id),
            daemon=True
        )
        thread.start()

    def speak_stream(self, token_generator, on_start=None, on_finish=None):
        """Streaming text token generator interface for continuous speech playback."""
        def text_collector():
            parts = []
            for token in token_generator:
                parts.append(token)
            return "".join(parts)

        try:
            full_text = text_collector()
            self.speak_async(full_text, on_start=on_start, on_finish=on_finish)
        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.warning(f"{ f"[JARVIS] speak_stream error: {e}" }" if isinstance(f"[JARVIS] speak_stream error: {e}", str) else f"[JARVIS] speak_stream error: {e}")
            else:
                import logging
                logging.getLogger(__name__).warning(f"{ f"[JARVIS] speak_stream error: {e}" }" if isinstance(f"[JARVIS] speak_stream error: {e}", str) else f"[JARVIS] speak_stream error: {e}")
            if on_finish:
                on_finish()

    def _synth_sentence(self, sentence: str) -> tuple[str | None, str]:
        """Synthesize a sentence to audio file path or return ('sapi5', sentence)."""
        if self._cancel_event.is_set():
            return (None, sentence)

        now = time.time()
        use_edge = _HAS_EDGE_TTS

        if os.environ.get("JARVIS_OFFLINE_TTS", "").lower() in ("true", "1", "yes") or \
           os.environ.get("JARVIS_FORCE_OFFLINE", "").lower() in ("true", "1", "yes"):
            use_edge = False

        if use_edge and now < self._edge_cooldown_until:
            use_edge = False

        if use_edge and (now - self._last_edge_check > 60.0):
            self._last_edge_check = now
            if not _is_bing_reachable(timeout=0.4):
                self._edge_cooldown_until = now + 60.0
                use_edge = False

        if use_edge:
            try:
                cache_key = uuid.uuid5(uuid.NAMESPACE_URL, f"{self.voice}|{self.rate}|{self.pitch}|{sentence}").hex
                mp3_path = self._temp_dir / f"tts_{cache_key}.mp3"
                if mp3_path.exists() and mp3_path.stat().st_size >= 100:
                    return (str(mp3_path), sentence)

                try:
                    communicate = edge_tts.Communicate(text=sentence, voice=self.voice, rate=self.rate, pitch=self.pitch)
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(communicate.save(str(mp3_path)))
                    finally:
                        loop.close()

                    if mp3_path.exists() and mp3_path.stat().st_size >= 100:
                        return (str(mp3_path), sentence)
                except Exception as ex_save:
                    logger.warning(f"EdgeTTS save error: {ex_save}")
            except Exception as e:
                err_str = str(e).lower()
                if any(w in err_str for w in ("getaddrinfo", "connect", "dns", "ssl", "timeout", "network")):
                    self._edge_cooldown_until = time.time() + 60.0

        return ("sapi5", sentence)


    def _speak_streaming_worker(self, text: str, on_start, on_finish, gen_id: int):
        """Parallel producer-consumer pipelined speech worker. Pre-fetches next sentences while current audio plays for ZERO gap after periods."""
        self._is_speaking = True
        if on_start:
            on_start()

        try:
            clean_text = clean_for_speech(text)
            if not clean_text:
                return

            sentences = split_sentences(clean_text)
            if not sentences:
                sentences = [clean_text]

            synth_queue = queue.Queue()
            SENTINEL = (None, None)

            def producer():
                for s in sentences:
                    if self._cancel_event.is_set() or gen_id != self._generation_id:
                        break
                    res = self._synth_sentence(s)
                    synth_queue.put(res)
                synth_queue.put(SENTINEL)

            prod_thread = threading.Thread(target=producer, daemon=True)
            prod_thread.start()

            while True:
                if self._cancel_event.is_set() or gen_id != self._generation_id:
                    break

                try:
                    # Efficient blocking queue fetch with 50ms timeout (0% CPU spin)
                    audio_type, s_text = synth_queue.get(block=True, timeout=0.05)
                except queue.Empty:
                    continue

                if audio_type is None and s_text is None:
                    break

                if audio_type == "sapi5":
                    if _OS == "Windows" and self._sapi_speaker:
                        self._speak_sapi5(s_text)
                    else:
                        self._speak_linux_fallback(s_text)
                elif audio_type:
                    self._play_and_wait(audio_type)

        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.warning(f"{ f"[JARVIS] TTS streaming error: {e}" }" if isinstance(f"[JARVIS] TTS streaming error: {e}", str) else f"[JARVIS] TTS streaming error: {e}")
            else:
                import logging
                logging.getLogger(__name__).warning(f"{ f"[JARVIS] TTS streaming error: {e}" }" if isinstance(f"[JARVIS] TTS streaming error: {e}", str) else f"[JARVIS] TTS streaming error: {e}")
            traceback.print_exc()
        finally:
            self._is_speaking = False
            self._current_alias = None
            if on_finish and gen_id == self._generation_id:
                on_finish()

    def _play_and_wait(self, filepath: str):
        """Play an audio file and wait for completion, checking cancel every 1ms."""
        if self._cancel_event.is_set():
            return

        try:
            alias = MCIPlayer.play_file(filepath)
            self._current_alias = alias
            while MCIPlayer.is_playing(alias):
                if self._cancel_event.is_set():
                    MCIPlayer.stop(alias)
                    return
                time.sleep(0.001)
            MCIPlayer.stop(alias)
        except Exception:
            pass

    def _speak_sapi5(self, text: str):
        """Speak using non-blocking interruptible SAPI5 (Windows HD Natural Offline Voice)."""
        if self._cancel_event.is_set():
            return
        try:
            if _HAS_PYTHONCOM:
                pythoncom.CoInitialize()
            if self._sapi_speaker:
                try:
                    self._sapi_speaker.Speak(text, 1)
                    while self._sapi_speaker.Status.RunningState == 2:
                        if self._cancel_event.is_set():
                            self._sapi_speaker.Speak("", 2)
                            return
                        time.sleep(0.001)
                    return
                except Exception as e:
                    if 'logger' in globals() or 'logger' in locals():
                        logger.info(f"{ f"[JARVIS] SAPI5 async speak notice: {e}" }" if isinstance(f"[JARVIS] SAPI5 async speak notice: {e}", str) else f"[JARVIS] SAPI5 async speak notice: {e}")
                    else:
                        import logging
                        logging.getLogger(__name__).info(f"{ f"[JARVIS] SAPI5 async speak notice: {e}" }" if isinstance(f"[JARVIS] SAPI5 async speak notice: {e}", str) else f"[JARVIS] SAPI5 async speak notice: {e}")

            import win32com.client
            local_speaker = win32com.client.Dispatch("SAPI.SpVoice")
            try:
                cat = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
                cat.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices", False)
                tokens = cat.EnumerateTokens()
                if tokens.Count > 0:
                    local_speaker.Voice = tokens.Item(0)
            except Exception:
                pass

            local_speaker.Rate = 2
            local_speaker.Speak(text, 1)
            while local_speaker.Status.RunningState == 2:
                if self._cancel_event.is_set():
                    local_speaker.Speak("", 2)
                    return
                time.sleep(0.001)
        except Exception as e:
            if 'logger' in globals() or 'logger' in locals():
                logger.warning(f"{ f"[JARVIS] SAPI5 speak error: {e}" }" if isinstance(f"[JARVIS] SAPI5 speak error: {e}", str) else f"[JARVIS] SAPI5 speak error: {e}")
            else:
                import logging
                logging.getLogger(__name__).warning(f"{ f"[JARVIS] SAPI5 speak error: {e}" }" if isinstance(f"[JARVIS] SAPI5 speak error: {e}", str) else f"[JARVIS] SAPI5 speak error: {e}")

    def _speak_linux_fallback(self, text: str):
        """Speak using espeak or spd-say (Linux CLI)."""
        if self._cancel_event.is_set():
            return
        cmd = None
        if shutil.which("spd-say"):
            cmd = ["spd-say", "-r", "15", text]
        elif shutil.which("espeak-ng"):
            cmd = ["espeak-ng", "-s", "175", text]
        elif shutil.which("espeak"):
            cmd = ["espeak", "-s", "175", text]

        if cmd:
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while proc.poll() is None:
                    if self._cancel_event.is_set():
                        proc.terminate()
                        return
                    time.sleep(0.02)
            except Exception:
                pass
