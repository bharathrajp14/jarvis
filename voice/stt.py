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

import os
import queue
_HAS_SR = False
try:
    import speech_recognition as sr
    _HAS_SR = True
    _BaseAudioSource = sr.AudioSource
except ImportError:
    sr = None
    _BaseAudioSource = object

_HAS_SD = False
try:
    import sounddevice as sd
    _HAS_SD = True
except ImportError:
    pass


class SounddeviceMicrophone(_BaseAudioSource):
    """Zero-dependency SpeechRecognition-compatible Microphone class using sounddevice.
    Bypasses PyAudio entirely, making voice input work seamlessly on modern Python versions (e.g. 3.14).
    """
    def __init__(self, device=None, sample_rate=16000, chunk_size=512):
        self.device_index = device
        
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
            except Exception as e:
                print(f"[SounddeviceMicrophone] Device query error: {e}")

                # 3. Fallback to any non-virtual input device
                if self.device_index is None:
                    for idx, dev in enumerate(devices):
                        if dev.get("max_input_channels", 0) > 0:
                            d_name = dev.get("name", "").lower()
                            if not any(vk in d_name for vk in virtual_keywords):
                                self.device_index = idx
                                break
            except Exception:
                self.device_index = None

        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2  # 16-bit PCM is 2 bytes
        self.q = queue.Queue()
        self.stream = None
        self.sd_stream = None

        # Query native sample rate of device
        self.device_sample_rate = self.SAMPLE_RATE
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
        import struct
        num_samples = len(data_bytes) // 2
        if num_samples == 0:
            return b""
        samples = struct.unpack(f"<{num_samples}h", data_bytes)
        ratio = self.device_sample_rate / self.SAMPLE_RATE
        
        out_samples = []
        pos = self._resample_phase
        while pos < num_samples:
            idx = int(pos)
            frac = pos - idx
            if idx + 1 < num_samples:
                val = int(samples[idx] * (1.0 - frac) + samples[idx + 1] * frac)
            else:
                val = samples[idx]
            out_samples.append(val)
            pos += ratio
            
        self._resample_phase = pos - num_samples
        if not out_samples:
            return b""
        return struct.pack(f"<{len(out_samples)}h", *out_samples)

    def _callback(self, indata, frames, time_info, status):
        raw_bytes = bytes(indata)
        if self.device_sample_rate != self.SAMPLE_RATE:
            try:
                raw_bytes = self._resample(raw_bytes)
            except Exception:
                pass
        self.q.put(raw_bytes)

    def read(self, size):
        bytes_to_read = size * self.SAMPLE_WIDTH
        data = b''
        while len(data) < bytes_to_read:
            try:
                chunk = self.q.get(timeout=0.1)
                data += chunk
            except queue.Empty:
                break
        return data[:bytes_to_read]

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
