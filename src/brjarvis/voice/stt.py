# voice/stt.py — JARVIS MK37 Speech-To-Text Audio Source (v2 — Low Latency)
"""
Speech recognition source adapters.
Bypasses PyAudio dependency by implementing a custom sounddevice-based
AudioSource compatibility class for SpeechRecognition.

v2: Optimized for low-latency wake-word detection.
    - Smaller chunk size (512) for faster VAD response.
    - Shorter queue read timeout (0.1s) for snappier recognition.
    - Drain helper for instant queue flush.
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import time

logger = logging.getLogger("JARVIS.Voice.STT")

_HAS_SR = False
try:
    import speech_recognition as sr  # type: ignore[import-not-found]
    _HAS_SR = True
    _BaseAudioSource = sr.AudioSource
except ImportError:
    sr = None
    _BaseAudioSource = object

_HAS_SD = False
try:
    import sounddevice as sd  # type: ignore[import-not-found]
    _HAS_SD = True
except ImportError:
    pass

import enum
from .audio_bus import AudioBus, AudioBusMicrophoneSource

class STTConfidence(str, enum.Enum):
    """Transcription confidence classification."""
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MEDIUM_CONFIDENCE = "MEDIUM_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN = "UNKNOWN"

class SounddeviceMicrophone(_BaseAudioSource):
    """Zero-dependency SpeechRecognition-compatible Microphone class using sounddevice.
    Bypasses PyAudio entirely, making voice input work seamlessly on modern Python versions (e.g. 3.14).
    """
    def __init__(self, device=None, sample_rate=16000, chunk_size=512):
        self.device_index = device
        
        # Validate explicit device index if provided
        if self.device_index is not None and _HAS_SD:
            try:
                devs = sd.query_devices()
                if isinstance(devs, list) and (0 <= self.device_index < len(devs)):
                    dev_info = devs[self.device_index]
                    if isinstance(dev_info, dict) and dev_info.get("max_input_channels", 0) <= 0:
                        self.device_index = None
                else:
                    self.device_index = None
            except Exception:
                self.device_index = None


        # 1. Environment override for audio input device
        env_device = os.environ.get("JARVIS_AUDIO_INPUT_DEVICE")
        if self.device_index is None and env_device:
            env_device_str = env_device.strip()
            if env_device_str:
                try:
                    if env_device_str.isdigit():
                        self.device_index = int(env_device_str)
                    elif _HAS_SD:
                        devices = sd.query_devices()
                        for idx, dev in enumerate(devices):
                            if dev.get("max_input_channels", 0) > 0 and env_device_str.lower() in dev.get('name', '').lower():
                                self.device_index = idx
                                break
                except Exception:
                    pass

        # 2. Smart auto-resolution: Probes active hardware mics, avoids silent virtual devices
        if self.device_index is None and _HAS_SD:
            try:
                devices = sd.query_devices()
                def_idx = getattr(sd.default, "device", [None])[0]
                virtual_keywords = ["virtual", "audiorelay", "cable", "mapper", "stereo mix"]
                physical_keywords = ["airbass", "headset", "microphone array", "realtek", "intel", "jabra", "bthhfenum"]

                # 1. Search for primary physical hardware mic
                for idx, dev in enumerate(devices):
                    if dev.get("max_input_channels", 0) > 0:
                        d_name = dev.get("name", "").lower()
                        if not any(vk in d_name for vk in virtual_keywords):
                            if any(pk in d_name for pk in physical_keywords):
                                self.device_index = idx
                                break

                # 2. Fallback to default device if non-virtual
                if self.device_index is None and def_idx is not None and 0 <= def_idx < len(devices):
                    def_dev = devices[def_idx]
                    def_name = def_dev.get("name", "").lower()
                    if def_dev.get("max_input_channels", 0) > 0 and not any(vk in def_name for vk in virtual_keywords):
                        self.device_index = def_idx

                # 3. Fallback to any non-virtual input device
                if self.device_index is None:
                    for idx, dev in enumerate(devices):
                        if dev.get("max_input_channels", 0) > 0:
                            d_name = dev.get("name", "").lower()
                            if not any(vk in d_name for vk in virtual_keywords):
                                self.device_index = idx
                                break
            except Exception as e:
                logger.warning(f"[SounddeviceMicrophone] Device query error: {e}")
                self.device_index = None

        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2  # 16-bit PCM is 2 bytes
        self.q = queue.Queue()
        self.stream = None
        self.sd_stream = None

        # Hot-plug recovery state
        self._recovery_enabled = os.environ.get("JARVIS_MIC_RECOVERY", "true").lower() in ("1", "true", "yes")
        self._is_alive = True
        self._reconnect_lock = threading.Lock()
        self._last_audio_time = time.monotonic()
        self._stale_threshold = float(os.environ.get("JARVIS_MIC_STALE_SECONDS", "5"))

        # Adaptive energy pre-filter (filters mic noise below calibrated floor)
        self._energy_filter_enabled = True
        self._noise_floor_rms = 0.0  # set by SileroVAD after calibration

        if _HAS_SD and self.device_index is not None:
            try:
                device_info = sd.query_devices(self.device_index, 'input')
                self.device_sample_rate = int(device_info.get('default_samplerate', self.SAMPLE_RATE))
            except Exception:
                pass

        self._resample_phase = 0.0

    def __enter__(self):
        if not _HAS_SR:
            raise ImportError(
                "speech_recognition is not installed. Run 'pip install SpeechRecognition' to use voice features."
            )
        if not _HAS_SD:
            raise ImportError(
                "sounddevice is not installed. Run 'pip install sounddevice' to use voice features."
            )
            
        # Try opening raw input stream with dynamic fallback samplerates and device fallback
        devices_to_try = [self.device_index]
        if self.device_index is not None:
            devices_to_try.append(None)  # System default mic fallback

        last_err = None
        for dev in devices_to_try:
            rates_to_try = [self.device_sample_rate, 16000, 44100, 48000, 32000, 8000]
            rates_to_try = list(dict.fromkeys([int(r) for r in rates_to_try if r is not None]))

            for rate in rates_to_try:
                try:
                    self.sd_stream = sd.RawInputStream(
                        samplerate=rate,
                        blocksize=self.CHUNK,
                        device=dev,
                        channels=1,
                        dtype='int16',
                        callback=self._callback
                    )
                    self.device_sample_rate = rate
                    self.device_index = dev
                    break
                except Exception as e:
                    last_err = e
                    self.sd_stream = None

            if self.sd_stream is not None:
                break

        if self.sd_stream is None:
            raise RuntimeError(f"Failed to open audio input stream: {last_err}")

        self.sd_stream.start()
        self.stream = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sd_stream:
            try:
                self.sd_stream.stop()
                self.sd_stream.close()
            except Exception:
                pass
            self.sd_stream = None
        self.stream = None

    def _resample(self, data_bytes: bytes) -> bytes:
        if not data_bytes:
            return b""
        try:
            import numpy as np  # type: ignore[import-not-found]
            samples = np.frombuffer(data_bytes, dtype=np.int16)
            if len(samples) == 0:
                return b""
            orig_len = len(samples)
            target_len = max(1, int(orig_len * (self.SAMPLE_RATE / self.device_sample_rate)))
            x_orig = np.linspace(0, orig_len - 1, num=orig_len)
            x_target = np.linspace(0, orig_len - 1, num=target_len)
            resampled = np.interp(x_target, x_orig, samples).astype(np.int16)
            return resampled.tobytes()
        except Exception:
            import struct
            num_samples = len(data_bytes) // 2
            if num_samples == 0:
                return b""
            samples = struct.unpack(f"<{num_samples}h", data_bytes)
            step = self.device_sample_rate / self.SAMPLE_RATE
            out_samples = [samples[int(i * step)] for i in range(int(num_samples / step)) if int(i * step) < num_samples]
            if not out_samples:
                return b""
            return struct.pack(f"<{len(out_samples)}h", *out_samples)

    def _callback(self, indata, frames, time_info, status):
        """Audio stream callback with hot-plug detection and energy pre-filter."""
        self._last_audio_time = time.monotonic()
        raw_bytes = bytes(indata)
        if self.device_sample_rate != self.SAMPLE_RATE:
            try:
                raw_bytes = self._resample(raw_bytes)
            except Exception:
                pass

        # Energy pre-filter: discard frames that are clearly just mic noise
        # This saves Whisper and VAD from processing silence
        if self._energy_filter_enabled and self._noise_floor_rms > 0:
            try:
                import numpy as _np
                samples = _np.frombuffer(raw_bytes, dtype=_np.int16).astype(_np.float32) / 32768.0
                rms = float(_np.sqrt(_np.mean(samples ** 2)))
                # Drop frame if RMS is below half the noise floor
                if rms < self._noise_floor_rms * 0.5:
                    return
            except Exception:
                pass

        self.q.put(raw_bytes)

    def read(self, size):
        bytes_to_read = size * self.SAMPLE_WIDTH
        data = bytearray()
        while len(data) < bytes_to_read:
            try:
                chunk = self.q.get(timeout=0.1)
                data.extend(chunk)
            except queue.Empty:
                break
        return bytes(data[:bytes_to_read])


    def drain(self):
        """Instantly flush all queued audio data. Call before listen() for fresh input."""
        dropped = 0
        while True:
            try:
                self.q.get_nowait()
                dropped += 1
            except queue.Empty:
                break
        return dropped

    def is_alive(self) -> bool:
        """Return True if the mic stream is actively delivering audio."""
        if self.sd_stream is None or not getattr(self.sd_stream, 'active', False):
            return False
        elapsed = time.monotonic() - self._last_audio_time
        return elapsed < self._stale_threshold

    def try_reconnect(self) -> bool:
        """
        Attempt hot-plug mic recovery after disconnect.
        Re-probes devices and reopens the audio stream.
        Returns True if reconnection succeeded.
        """
        if not self._recovery_enabled:
            return False
        with self._reconnect_lock:
            logger.warning("[STT] Mic stale/disconnected. Attempting hot-plug recovery...")
            # Close dead stream
            if self.sd_stream:
                try:
                    self.sd_stream.stop()
                    self.sd_stream.close()
                except Exception:
                    pass
                self.sd_stream = None

            # Re-probe: USB mics may get new index after replug
            self.device_index = None
            if _HAS_SD:
                try:
                    devices = sd.query_devices()
                    virtual_keywords = ["virtual", "audiorelay", "cable", "mapper", "stereo mix"]
                    for idx, dev in enumerate(devices):
                        if dev.get("max_input_channels", 0) > 0:
                            d_name = dev.get("name", "").lower()
                            if not any(vk in d_name for vk in virtual_keywords):
                                self.device_index = idx
                                break
                except Exception:
                    pass

            # Try reopening stream
            for rate in [self.device_sample_rate, 16000, 44100, 48000]:
                try:
                    if not _HAS_SD:
                        break
                    self.sd_stream = sd.RawInputStream(
                        samplerate=rate,
                        blocksize=self.CHUNK,
                        device=self.device_index,
                        channels=1,
                        dtype='int16',
                        callback=self._callback,
                    )
                    self.device_sample_rate = rate
                    self.sd_stream.start()
                    self._last_audio_time = time.monotonic()
                    logger.info(
                        "[STT] Hot-plug recovery OK — device=%s rate=%d",
                        self.device_index, rate
                    )
                    return True
                except Exception as e:
                    logger.debug("[STT] Recovery attempt at %dHz failed: %s", rate, e)
                    self.sd_stream = None

            logger.error("[STT] Hot-plug recovery FAILED — no input device available")
            return False

    def set_noise_floor(self, rms: float) -> None:
        """Update the energy pre-filter noise floor from the NoiseCalibrator."""
        self._noise_floor_rms = max(0.0, float(rms))


class SpeechToTextEngine:
    """Convenience wrapper for transcribing audio files using whisper or speech_recognition."""

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text."""
        try:
            from brjarvis.voice.whisper_local import transcribe_file
            res = transcribe_file(audio_path)
            if res:
                return res
        except Exception:
            pass

        if _HAS_SR and sr is not None:
            try:
                r = sr.Recognizer()
                with sr.AudioFile(audio_path) as source:
                    audio = r.record(source)
                return r.recognize_google(audio)
            except Exception as e:
                return f"[STT Error: {e}]"
        return "[STT Error: No speech recognition engine available]"

