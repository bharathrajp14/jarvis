# voice/audio_bus.py — Unified Audio Capture & Broadcast Bus for BR JARVIS MK40.2
"""
Unified Single-Stream Audio Capture and Broadcast Bus.

Opens exactly ONE physical microphone stream on the host soundcard,
eliminating audio device contention and multi-stream crashes on Windows.
Dispatches timestamped, sequence-numbered PCM audio frames to subscribers:
1. Wake Detector
2. Command STT Capture
3. Barge-In VAD Detector
4. Noise Floor Calibrator

Includes Software Acoustic Echo Gating to prevent self-interruption during TTS playback.
"""

from __future__ import annotations

import collections
import dataclasses
import logging
import os
import queue
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger("JARVIS.Voice.AudioBus")

_HAS_SD = False
try:
    import sounddevice as sd  # type: ignore[import-not-found]

    _HAS_SD = True
except ImportError:
    pass

_HAS_SR = False
try:
    import speech_recognition as sr  # type: ignore[import-not-found]

    _HAS_SR = True
    _BaseAudioSource = sr.AudioSource
except ImportError:
    _BaseAudioSource = object


@dataclasses.dataclass(frozen=True)
class AudioFrame:
    """Timestamped audio frame containing raw PCM bytes and metadata."""

    sequence_id: int
    timestamp: float
    data: bytes
    sample_rate: int
    duration_ms: float
    is_echo_gated: bool = False


class AudioSubscriber:
    """Subscriber queue receiving broadcast frames from the AudioBus."""

    def __init__(self, name: str, max_frames: int = 120):
        self.name = name
        self.max_frames = max_frames
        self._queue: queue.Queue[AudioFrame] = queue.Queue(maxsize=max_frames)
        self._dropped_frames: int = 0

    def put(self, frame: AudioFrame) -> bool:
        """Enqueue frame. If full, drop the oldest frame to prevent unbounded lag."""
        try:
            self._queue.put_nowait(frame)
            return True
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._dropped_frames += 1
                self._queue.put_nowait(frame)
                return True
            except (queue.Empty, queue.Full):
                return False

    def get(self, timeout: Optional[float] = None) -> AudioFrame:
        return self._queue.get(timeout=timeout)

    def get_nowait(self) -> Optional[AudioFrame]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def drain(self) -> int:
        """Drain all queued frames immediately."""
        count = 0
        while True:
            try:
                self._queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        return count

    def is_empty(self) -> bool:
        return self._queue.empty()

    @property
    def qsize(self) -> int:
        return self._queue.qsize()


class AudioBus:
    """
    Centralized single-capture audio broadcast system.

    Maintains a single physical audio input stream and distributes PCM frames
    to registered subscribers.
    """

    _instance: Optional[AudioBus] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(
        cls, sample_rate: int = 16000, chunk_size: int = 512, device_index: Optional[int] = None
    ) -> AudioBus:
        if cls._instance is not None:
            return cls._instance
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = AudioBus(sample_rate=sample_rate, chunk_size=chunk_size, device_index=device_index)
        return cls._instance

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 512, device_index: Optional[int] = None):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.device_sample_rate = sample_rate

        self._subscribers: Dict[str, AudioSubscriber] = {}
        self._lock = threading.RLock()
        self._is_running = False
        self._sd_stream = None

        # Monotonic sequence numbering & stats
        self._seq_counter = 0
        self._last_audio_time = time.monotonic()
        self._stale_threshold = float(os.environ.get("JARVIS_MIC_STALE_SECONDS", "5.0"))
        self._reconnect_lock = threading.Lock()

        # Acoustic Echo Gating Flag: Set to True while TTS is actively outputting audio
        self._echo_gate_active = False

        # Rolling pre-roll buffer for zero-truncation wake capture (e.g. 500ms)
        self._preroll_buffer: collections.deque[AudioFrame] = collections.deque(maxlen=30)

        # Pre-resolve best audio hardware device
        self._resolve_device()

    def _resolve_device(self) -> None:
        """Resolve physical microphone device index."""
        if not _HAS_SD:
            return

        env_device = os.environ.get("JARVIS_AUDIO_INPUT_DEVICE")
        if env_device:
            env_dev_str = env_device.strip()
            if env_dev_str.isdigit():
                self.device_index = int(env_dev_str)
                return

        if self.device_index is None:
            try:
                devices = sd.query_devices()
                def_idx = getattr(sd.default, "device", [None])[0]
                virtual_keywords = ["virtual", "audiorelay", "cable", "mapper", "stereo mix"]
                physical_keywords = ["airbass", "headset", "microphone array", "realtek", "intel", "jabra", "bthhfenum"]

                # 1. Search for hardware mic matching physical keyword
                for idx, dev in enumerate(devices):
                    if dev.get("max_input_channels", 0) > 0:
                        d_name = dev.get("name", "").lower()
                        if not any(vk in d_name for vk in virtual_keywords):
                            if any(pk in d_name for pk in physical_keywords):
                                self.device_index = idx
                                return

                # 2. Fallback to default device if valid
                if def_idx is not None and 0 <= def_idx < len(devices):
                    def_dev = devices[def_idx]
                    if def_dev.get("max_input_channels", 0) > 0:
                        d_name = def_dev.get("name", "").lower()
                        if not any(vk in d_name for vk in virtual_keywords):
                            self.device_index = def_idx
                            return

                # 3. Any non-virtual input device
                for idx, dev in enumerate(devices):
                    if dev.get("max_input_channels", 0) > 0:
                        d_name = dev.get("name", "").lower()
                        if not any(vk in d_name for vk in virtual_keywords):
                            self.device_index = idx
                            return
            except Exception as e:
                logger.warning("[AudioBus] Device resolution error: %s", e)

    def set_echo_gate(self, active: bool) -> None:
        """Enable/disable Acoustic Echo Gating (called by TTS engine on start/stop)."""
        self._echo_gate_active = bool(active)

    @property
    def is_echo_gate_active(self) -> bool:
        return self._echo_gate_active

    def subscribe(self, name: str, max_frames: int = 120) -> AudioSubscriber:
        """Register a subscriber to receive real-time audio frames."""
        with self._lock:
            if name in self._subscribers:
                return self._subscribers[name]
            sub = AudioSubscriber(name=name, max_frames=max_frames)
            self._subscribers[name] = sub
            logger.debug("[AudioBus] Subscriber '%s' connected (total=%d)", name, len(self._subscribers))
            return sub

    def unsubscribe(self, name: str) -> None:
        """Unregister a subscriber."""
        with self._lock:
            self._subscribers.pop(name, None)

    def start(self) -> bool:
        """Start the single shared physical audio input stream."""
        with self._lock:
            if self._is_running and self._sd_stream is not None:
                return True

            if not _HAS_SD:
                logger.warning("[AudioBus] sounddevice not available. Bus running in dummy mode.")
                self._is_running = True
                return False

            devices_to_try = [self.device_index]
            if self.device_index is not None:
                devices_to_try.append(None)  # System default mic fallback

            last_err = None
            for dev in devices_to_try:
                rates_to_try = [self.device_sample_rate, 16000, 44100, 48000, 32000, 8000]
                rates_to_try = list(dict.fromkeys([int(r) for r in rates_to_try if r is not None]))

                for rate in rates_to_try:
                    try:
                        self._sd_stream = sd.RawInputStream(
                            samplerate=rate,
                            blocksize=self.chunk_size,
                            device=dev,
                            channels=1,
                            dtype="int16",
                            callback=self._audio_callback,
                        )
                        self.device_sample_rate = rate
                        self.device_index = dev
                        self._sd_stream.start()
                        self._is_running = True
                        self._last_audio_time = time.monotonic()
                        logger.info(
                            "[AudioBus] Audio capture started on device=%s, rate=%dHz, blocksize=%d",
                            dev,
                            rate,
                            self.chunk_size,
                        )
                        return True
                    except Exception as e:
                        last_err = e
                        self._sd_stream = None

            logger.error("[AudioBus] Failed to open physical audio stream: %s", last_err)
            return False

    def stop(self) -> None:
        """Stop the audio input stream and flush subscribers."""
        with self._lock:
            self._is_running = False
            if self._sd_stream is not None:
                try:
                    self._sd_stream.stop()
                    self._sd_stream.close()
                except Exception:
                    pass
                self._sd_stream = None
            logger.info("[AudioBus] Audio capture stopped.")

    def is_alive(self) -> bool:
        """Return True if the microphone stream is actively receiving frames."""
        if not self._is_running:
            return False
        if self._sd_stream is None:
            return False
        elapsed = time.monotonic() - self._last_audio_time
        return elapsed < self._stale_threshold

    def try_reconnect(self) -> bool:
        """Hot-plug recovery: re-probes devices and re-opens stream cleanly."""
        with self._reconnect_lock:
            logger.warning("[AudioBus] Attempting hot-plug microphone reconnection...")
            self.stop()
            self._resolve_device()
            return self.start()

    def get_preroll_bytes(self) -> bytes:
        """Get accumulated pre-roll audio frames (e.g. 500ms before wake detection)."""
        with self._lock:
            return b"".join(f.data for f in self._preroll_buffer)

    def clear_preroll(self) -> None:
        with self._lock:
            self._preroll_buffer.clear()

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        """Single raw sounddevice callback executing on audio thread."""
        self._last_audio_time = time.monotonic()
        raw_bytes = bytes(indata)

        if self.device_sample_rate != self.sample_rate:
            raw_bytes = self._resample(raw_bytes, self.device_sample_rate, self.sample_rate)

        self._seq_counter += 1
        duration_ms = (len(raw_bytes) / (self.sample_rate * 2)) * 1000.0

        frame = AudioFrame(
            sequence_id=self._seq_counter,
            timestamp=self._last_audio_time,
            data=raw_bytes,
            sample_rate=self.sample_rate,
            duration_ms=duration_ms,
            is_echo_gated=self._echo_gate_active,
        )

        with self._lock:
            self._preroll_buffer.append(frame)
            subscribers = list(self._subscribers.values())

        for sub in subscribers:
            sub.put(frame)

    @staticmethod
    def _resample(data_bytes: bytes, src_rate: int, dst_rate: int) -> bytes:
        """Resample 16-bit PCM bytes from src_rate to dst_rate."""
        if not data_bytes or src_rate == dst_rate:
            return data_bytes
        try:
            import numpy as np

            samples = np.frombuffer(data_bytes, dtype=np.int16)
            if len(samples) == 0:
                return b""
            orig_len = len(samples)
            target_len = max(1, int(orig_len * (dst_rate / src_rate)))
            x_orig = np.linspace(0, orig_len - 1, num=orig_len)
            x_target = np.linspace(0, orig_len - 1, num=target_len)
            resampled = np.interp(x_target, x_orig, samples).astype(np.int16)
            return resampled.tobytes()
        except Exception:
            return data_bytes


class AudioBusMicrophoneSource(_BaseAudioSource):
    """
    SpeechRecognition-compatible AudioSource adapter powered by AudioBus.

    Allows speech_recognition.Recognizer to read PCM audio directly from the
    shared AudioBus without opening a duplicate hardware stream.
    """

    def __init__(self, subscriber_name: str = "sr_source", sample_rate: int = 16000, chunk_size: int = 512):
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2
        self.subscriber_name = subscriber_name
        self.bus = AudioBus.get_instance(sample_rate=sample_rate, chunk_size=chunk_size)
        self.sub = self.bus.subscribe(subscriber_name)
        self.stream = self
        self._buffer = bytearray()

    @property
    def device_index(self) -> Optional[int]:
        return self.bus.device_index

    def __enter__(self):
        self.bus.start()
        self.sub.drain()
        self._buffer.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sub.drain()
        self._buffer.clear()

    def read(self, size: int) -> bytes:
        bytes_to_read = size * self.SAMPLE_WIDTH
        start_time = time.monotonic()
        while len(self._buffer) < bytes_to_read and (time.monotonic() - start_time) < 1.0:
            try:
                frame = self.sub.get(timeout=0.1)
                if frame is not None:
                    self._buffer.extend(frame.data)
            except (queue.Empty, Exception):
                # Non-fatal: queue timeout
                if len(self._buffer) >= bytes_to_read:
                    break
                time.sleep(0.01)

        if not self._buffer:
            return b"\x00" * bytes_to_read

        out = bytes(self._buffer[:bytes_to_read])
        del self._buffer[:bytes_to_read]
        if len(out) < bytes_to_read:
            out += b"\x00" * (bytes_to_read - len(out))
        return out

    def drain(self) -> int:
        self._buffer.clear()
        return self.sub.drain()

    def is_alive(self) -> bool:
        return self.bus.is_alive()

    def try_reconnect(self) -> bool:
        return self.bus.try_reconnect()
