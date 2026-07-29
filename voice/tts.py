# voice/tts.py — JARVIS MK37 Neural Text-To-Speech Engine (v2 — Sentence Streaming)
"""
High-quality text-to-speech using Microsoft Edge neural voices.
v2: Sentence-level streaming for <300ms time-to-first-audio.
    Instant barge-in cancel on new task.
    Smart text cleaning for AI assistant output.
"""
from __future__ import annotations

import asyncio
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
import time
import traceback
from pathlib import Path

_OS = platform.system()

_HAS_EDGE_TTS = False
try:
    import edge_tts
    _HAS_EDGE_TTS = True
except ImportError:
    pass

_HAS_PYTHONCOM = False
try:
    import pythoncom
    _HAS_PYTHONCOM = True
except ImportError:
    pass


# ── Smart text cleaner for AI assistant output ────────────────────────────
_CODE_BLOCK_RX = re.compile(r'```.*?```', re.DOTALL)
_TOOL_CALL_RX  = re.compile(r'```tool_call\s*\n\s*\{.*?\}\s*\n\s*```', re.DOTALL)
_XML_TOKEN_RX  = re.compile(r'<\|.*?\|>', re.DOTALL)
_CHANNEL_RX    = re.compile(r'<\|channel\|>.*?<\|call\|>', re.DOTALL)
_MESSAGE_RX    = re.compile(r'<\|message\|>.*?<\|call\|>', re.DOTALL)
_START_RX      = re.compile(r'<\|start\|>.*?<\|call\|>', re.DOTALL)
_JSON_BLOCK_RX = re.compile(r'\{["\']tool["\']\s*:\s*["\'][^"\']+["\']\s*,\s*["\']args["\']\s*:\s*\{.*?\}\s*\}', re.DOTALL)
_MD_CHARS_RX   = re.compile(r'[*_~`#\[\](){}<>|]')
_LINK_RX       = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_URL_RX        = re.compile(r'https?://\S+')
_FILE_PATH_RX  = re.compile(r'(?:[A-Z]:\\|[a-zA-Z0-9_-]+[/\\])[^\s,;]+')
_EMOJI_RX      = re.compile(r'[\U0001F300-\U0001FAFF\U00002702-\U000027B0]')
_WHITESPACE_RX = re.compile(r'\s{2,}')

_SYSTEM_TAGS_RX = re.compile(r'\[DONE[^\]]*\]|⚡\s*\[Antigravity Instant 0-Token Action\]|\[Tool:[^\]]*\]|\[Executed Tool:[^\]]*\]', re.IGNORECASE)

def _format_path_for_speech(match: re.Match) -> str:
    path_str = match.group(0)
    try:
        fname = Path(path_str).name
        if fname:
            return fname.replace('_', ' ')
    except Exception:
        pass
    return path_str

def clean_for_speech(text: str) -> str:
    """Remove tool calls, code blocks, markdown, URLs, JSON blocks, system tags, and emojis from text for clean speech output, converting file paths to natural spoken names."""
    t = _CODE_BLOCK_RX.sub('', text)
    t = _TOOL_CALL_RX.sub('', t)
    t = _START_RX.sub('', t)
    t = _CHANNEL_RX.sub('', t)
    t = _MESSAGE_RX.sub('', t)
    t = _XML_TOKEN_RX.sub('', t)
    t = _JSON_BLOCK_RX.sub('', t)
    t = _SYSTEM_TAGS_RX.sub('', t)
    t = _LINK_RX.sub(r'\1', t)       # [link text](url) → link text
    t = _URL_RX.sub('', t)
    t = _FILE_PATH_RX.sub(_format_path_for_speech, t)
    t = _EMOJI_RX.sub('', t)
    t = _MD_CHARS_RX.sub('', t)
    t = _WHITESPACE_RX.sub(' ', t)
    return t.strip()


def summarize_for_speech(text: str, max_chars: int = 1000) -> str:
    """Truncate long technical responses to a concise conversational speech summary ending on clean sentence boundaries."""
    clean = clean_for_speech(text)
    if not clean or len(clean) <= max_chars:
        return clean
    
    sentences = split_sentences(clean)
    summary = ""
    for s in sentences:
        if len(summary) + len(s) + 1 <= max_chars:
            summary += (s + " ")
        else:
            break
    
    if not summary.strip():
        # Fallback to nearest word boundary
        words = clean[:max_chars].rsplit(" ", 1)[0]
        summary = words + "." if not words.endswith(('.', '!', '?')) else words
        
    return summary.strip()


# ── Sentence splitter for streaming TTS ───────────────────────────────────
_SENTENCE_RX = re.compile(r'([^.!?\n]+[.!?\n]+)')

def split_sentences(text: str) -> list[str]:
    """Split text into speakable sentence chunks."""
    sentences = _SENTENCE_RX.findall(text)
    remainder = _SENTENCE_RX.sub('', text).strip()
    if remainder:
        sentences.append(remainder)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]


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


class MCIPlayer:
    """Play MP3/WAV files using sounddevice, Windows MCI, or system audio utilities."""
    _winmm = None
    _lock = threading.Lock()
    _active_processes: dict[str, subprocess.Popen] = {}
    _active_audio_threads: dict[str, tuple[threading.Thread, threading.Event]] = {}

    @classmethod
    def _init_winmm(cls):
        if cls._winmm is None and _OS == "Windows":
            import ctypes
            cls._winmm = ctypes.windll.winmm

    @classmethod
    def _send(cls, command: str) -> str:
        if _OS != "Windows":
            return ""
        import ctypes
        cls._init_winmm()
        buf = ctypes.create_unicode_buffer(256)
        err = cls._winmm.mciSendStringW(command, buf, 255, 0)
        if err:
            err_buf = ctypes.create_unicode_buffer(256)
            cls._winmm.mciGetErrorStringW(err, err_buf, 255)
            raise RuntimeError(f"MCI error: {err_buf.value}")
        return buf.value

    @classmethod
    def play_file(cls, filepath: str, alias: str = None) -> str:
        """Play an audio file across platforms. Supports targeted output hardware (e.g. AirBass Earbuds)."""
        with cls._lock:
            alias = alias or f"tts_{uuid.uuid4().hex[:8]}"
            target_dev = resolve_output_device()

            # 1. Direct sounddevice PCM playback for targeted output hardware (AirBass Earbuds)
            if target_dev is not None:
                try:
                    import sounddevice as sd
                    import numpy as np
                    ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffplay")
                    if ffmpeg_bin:
                        cmd = [ffmpeg_bin, "-y", "-i", filepath, "-f", "s16le", "-ac", "1", "-ar", "24000", "-"]
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                        pcm, _ = proc.communicate(timeout=10)
                        if pcm:
                            audio_data = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
                            stop_evt = threading.Event()

                            def _play_worker(a_name=alias, data=audio_data, dev=target_dev, evt=stop_evt):
                                try:
                                    sd.play(data, samplerate=24000, device=dev)
                                    duration = len(data) / 24000.0
                                    end_t = time.time() + duration
                                    while time.time() < end_t and not evt.is_set():
                                        time.sleep(0.01)
                                    if evt.is_set():
                                        sd.stop()
                                except Exception:
                                    pass
                                finally:
                                    with cls._lock:
                                        cls._active_audio_threads.pop(a_name, None)

                            th = threading.Thread(target=_play_worker, daemon=True)
                            cls._active_audio_threads[alias] = (th, stop_evt)
                            th.start()
                            return alias
                except Exception as e:
                    pass

            # 2. Process / MCI fallback if no targeted device or sounddevice fails
            ffplay_bin = shutil.which("ffplay")
            if ffplay_bin:
                cmd = [ffplay_bin, "-nodisp", "-autoexit", "-loglevel", "quiet", filepath]
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    cls._active_processes[alias] = proc
                    return alias
                except Exception:
                    pass

            if _OS == "Windows":
                fp = filepath.replace("/", "\\")
                try:
                    cls._send(f'close {alias}')
                except RuntimeError:
                    pass
                cls._send(f'open "{fp}" type mpegvideo alias {alias}')
                cls._send(f'play {alias}')
                return alias
            else:
                players = ["pw-play", "paplay", "mpv", "aplay", "canberra-gtk-play", "vlc"]
                chosen = None
                for p in players:
                    if shutil.which(p):
                        chosen = p
                        break

                if chosen:
                    cmd = [chosen]
                    if chosen == "mpv":
                        cmd.extend(["--no-terminal", "--no-video"])
                    cmd.append(filepath)

                    try:
                        proc = subprocess.Popen(
                            cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        cls._active_processes[alias] = proc
                    except Exception:
                        pass
                return alias

    @classmethod
    def is_playing(cls, alias: str) -> bool:
        """Check if the given alias is currently playing."""
        with cls._lock:
            if alias in cls._active_audio_threads:
                th, evt = cls._active_audio_threads[alias]
                if th.is_alive() and not evt.is_set():
                    return True
                else:
                    cls._active_audio_threads.pop(alias, None)
                    return False

            proc = cls._active_processes.get(alias)
            if proc is not None:
                if proc.poll() is None:
                    return True
                else:
                    cls._active_processes.pop(alias, None)
                    return False

        if _OS == "Windows":
            try:
                status = cls._send(f'status {alias} mode')
                return status.strip().lower() == "playing"
            except RuntimeError:
                return False
        return False

    @classmethod
    def play_file_blocking(cls, filepath: str):
        """Play a file and block until playback completes."""
        alias = cls.play_file(filepath)
        while cls.is_playing(alias):
            time.sleep(0.02)
        cls.stop(alias)

    @classmethod
    def stop(cls, alias: str):
        """Stop and close the given alias instantly."""
        with cls._lock:
            if alias in cls._active_audio_threads:
                th, evt = cls._active_audio_threads.pop(alias)
                evt.set()
                try:
                    import sounddevice as sd
                    sd.stop()
                except Exception:
                    pass

            proc = cls._active_processes.pop(alias, None)
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

        if _OS == "Windows":
            try:
                cls._send(f'stop {alias}')
                cls._send(f'close {alias}')
            except RuntimeError:
                pass

    @classmethod
    def stop_all(cls):
        """Stop ALL active playback aliases."""
        if _OS == "Windows":
            try:
                cls._send('close all')
            except RuntimeError:
                pass
        else:
            with cls._lock:
                for alias, proc in list(cls._active_processes.items()):
                    if proc and proc.poll() is None:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                cls._active_processes.clear()


class NeuralTTS:
    """High-quality text-to-speech using Microsoft Edge neural voices.
    Falls back to Linux espeak/spd-say or Windows SAPI5.
    
    v2 improvements:
    - Sentence-level streaming: splits text into sentences and synthesizes/plays
      each sentence independently for <300ms time-to-first-audio.
    - Instant barge-in: stop() cancels synthesis and playback immediately.
    - Task isolation: new speak_async() call auto-cancels any previous speech.
    - Smart text cleaner: strips tool calls, markdown, URLs, file paths, emojis.
    """

    VOICES = {
        "default":   "en-GB-SoniaNeural",      # British female — elegant, JARVIS-like
        "male_gb":   "en-GB-RyanNeural",        # British male
        "female_us": "en-US-JennyNeural",      # American female
        "male_us":   "en-US-GuyNeural",         # American male
    }

    def __init__(self, voice_key: str = "default", rate: str = "+18%", pitch: str = "+0Hz"):
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
        self._prune_cache()
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
        """Initialize SAPI5 as fallback (Windows)."""
        try:
            if _HAS_PYTHONCOM:
                pythoncom.CoInitialize()
            import win32com.client
            self._sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voices = self._sapi_speaker.GetVoices()
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription()
                if "Zira" in desc or "Hazel" in desc:
                    self._sapi_speaker.Voice = voices.Item(i)
                    break
            self._sapi_speaker.Rate = -1
            print("[JARVIS] SAPI5 fallback voice initialized.")
        except Exception as e:
            print(f"[JARVIS] Warning: SAPI5 fallback failed: {e}")
            self._sapi_speaker = None

    def _init_linux_tts(self):
        """Initialize Linux speech dispatcher or espeak fallback."""
        if shutil.which("spd-say") or shutil.which("espeak") or shutil.which("espeak-ng"):
            print("[JARVIS] Linux native CLI TTS engine ready.")

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def stop(self):
        """Instantly stop any active speech playback (Barge-In interruption).
        Cancels both synthesis and playback immediately.
        """
        self._cancel_event.set()
        self._is_speaking = False
        if self._current_alias:
            MCIPlayer.stop(self._current_alias)
            self._current_alias = None
        MCIPlayer.stop_all()
        if self._sapi_speaker:
            try:
                self._sapi_speaker.Speak("", 2)  # SAPI purge flag
            except Exception:
                pass

    def speak_async(self, text: str, on_start=None, on_finish=None):
        """Speak text in a background thread with sentence-level streaming.
        
        Auto-cancels any previous speech before starting (task isolation).
        """
        # Cancel any in-progress speech immediately
        if self._is_speaking:
            self.stop()

        self._cancel_event.clear()
        with self._gen_lock:
            self._generation_id += 1
            gen_id = self._generation_id

        thread = threading.Thread(
            target=self._speak_streaming_worker,
            args=(text, on_start, on_finish, gen_id),
            daemon=True
        )
        thread.start()

    def _speak_streaming_worker(self, text: str, on_start, on_finish, gen_id: int):
        """Worker that cleans text, splits into sentences, and synthesizes/plays each independently."""
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

            for sentence in sentences:
                # Check cancel signal before each sentence
                if self._cancel_event.is_set() or gen_id != self._generation_id:
                    break

                self._speak_single_sentence(sentence)

        except Exception as e:
            print(f"[JARVIS] TTS streaming error: {e}")
            traceback.print_exc()
        finally:
            self._is_speaking = False
            self._current_alias = None
            if on_finish and gen_id == self._generation_id:
                on_finish()

    def _speak_single_sentence(self, sentence: str):
        """Synthesize and play a single sentence. Checks cancel between synthesis and playback."""
        if self._cancel_event.is_set():
            return

        success = False
        if _HAS_EDGE_TTS:
            try:
                self._synth_and_play_edge(sentence)
                success = True
            except Exception as e:
                print(f"[JARVIS] Edge-TTS sentence failed ({e}). Falling back...")
        
        if not success:
            if _OS == "Windows" and self._sapi_speaker:
                self._speak_sapi5(sentence)
            else:
                self._speak_linux_fallback(sentence)

    def _synth_and_play_edge(self, sentence: str):
        """Synthesize one sentence with edge-tts, cache it, and play."""
        if self._cancel_event.is_set():
            return

        cache_key = uuid.uuid5(uuid.NAMESPACE_URL, f"{self.voice}|{self.rate}|{self.pitch}|{sentence}").hex
        mp3_path = self._temp_dir / f"tts_{cache_key}.mp3"

        # Check cache first (instant playback for repeated phrases)
        if mp3_path.exists() and mp3_path.stat().st_size >= 100:
            self._play_and_wait(str(mp3_path))
            return

        # Synthesize
        if self._cancel_event.is_set():
            return

        for attempt in range(2):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                communicate = edge_tts.Communicate(
                    text=sentence,
                    voice=self.voice,
                    rate=self.rate,
                    pitch=self.pitch,
                )
                loop.run_until_complete(communicate.save(str(mp3_path)))
                break
            except Exception as e:
                if mp3_path.exists():
                    try:
                        mp3_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                if attempt == 0:
                    time.sleep(0.25)
                else:
                    raise e
            finally:
                loop.close()

        if self._cancel_event.is_set():
            return

        if not mp3_path.exists() or mp3_path.stat().st_size < 100:
            raise RuntimeError("Edge-TTS produced an invalid or empty audio file.")

        self._prune_cache()
        self._play_and_wait(str(mp3_path))

    def _play_and_wait(self, filepath: str):
        """Play an audio file and wait for completion, checking cancel every 20ms."""
        if self._cancel_event.is_set():
            return

        try:
            alias = MCIPlayer.play_file(filepath)
            self._current_alias = alias
            while MCIPlayer.is_playing(alias):
                if self._cancel_event.is_set():
                    MCIPlayer.stop(alias)
                    return
                time.sleep(0.02)
            MCIPlayer.stop(alias)
        except Exception:
            pass

    def _speak_sapi5(self, text: str):
        """Speak using SAPI5 (Windows blocking)."""
        if self._cancel_event.is_set():
            return
        try:
            if _HAS_PYTHONCOM:
                pythoncom.CoInitialize()
            if self._sapi_speaker:
                try:
                    self._sapi_speaker.Speak(text, 0)
                    return
                except Exception:
                    pass
            # Fallback to local dispatch on current thread if main instance fails
            import win32com.client
            local_speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voices = local_speaker.GetVoices()
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription()
                if "Zira" in desc or "Hazel" in desc:
                    local_speaker.Voice = voices.Item(i)
                    break
            local_speaker.Rate = -1
            local_speaker.Speak(text, 0)
        except Exception as e:
            print(f"[JARVIS] SAPI5 speak error: {e}")

    def _speak_linux_fallback(self, text: str):
        """Speak using Linux spd-say or espeak fallback."""
        if self._cancel_event.is_set():
            return
        clean = re.sub(r'[*_~`#\[\](){}<>|]', '', text).strip()
        if not clean:
            return
        
        if shutil.which("spd-say"):
            subprocess.run(["spd-say", "-w", clean], capture_output=True)
        elif shutil.which("espeak-ng"):
            subprocess.run(["espeak-ng", clean], capture_output=True)
        elif shutil.which("espeak"):
            subprocess.run(["espeak", clean], capture_output=True)

    def speak_stream(self, token_generator, on_start=None, on_finish=None):
        """Stream LLM tokens, split into sentences, and synthesize/play audio
        on sentence boundaries for <300ms time-to-first-audio latency."""
        # Cancel any prior speech
        if self._is_speaking:
            self.stop()

        self._cancel_event.clear()
        with self._gen_lock:
            self._generation_id += 1
            gen_id = self._generation_id

        def _stream_worker():
            self._is_speaking = True
            if on_start:
                on_start()
            
            buffer = ""

            try:
                for token in token_generator:
                    if self._cancel_event.is_set() or gen_id != self._generation_id:
                        break
                    buffer += token
                    
                    matches = _SENTENCE_RX.findall(buffer)
                    if matches:
                        for sentence in matches:
                            if self._cancel_event.is_set() or gen_id != self._generation_id:
                                break
                            clean_s = clean_for_speech(sentence)
                            if clean_s and len(clean_s) > 1:
                                self._speak_single_sentence(clean_s)
                            buffer = buffer[len(sentence):]

                if buffer.strip() and not self._cancel_event.is_set() and gen_id == self._generation_id:
                    clean_s = clean_for_speech(buffer)
                    if clean_s:
                        self._speak_single_sentence(clean_s)
            except Exception as e:
                print(f"[NeuralTTS] Stream TTS error: {e}")
            finally:
                self._is_speaking = False
                if on_finish and gen_id == self._generation_id:
                    on_finish()

        threading.Thread(target=_stream_worker, daemon=True).start()
