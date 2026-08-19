# voice/ring_buffer.py — Rolling 500ms Audio Pre-Roll Ring Buffer for JARVIS
"""
High-performance thread-safe rolling PCM audio ring buffer.
Maintains a 500ms pre-roll audio queue (16kHz 16-bit mono PCM = 16,000 bytes/sec).
Ensures zero audio truncation during wake word and push-to-talk transitions.
"""

from __future__ import annotations

import collections
import threading


class AudioRingBuffer:
    """Thread-safe rolling PCM audio pre-roll ring buffer."""

    def __init__(
        self, sample_rate: int = 16000, sample_width: int = 2, channels: int = 1, buffer_duration_ms: int = 500
    ):
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.bytes_per_second = sample_rate * sample_width * channels
        self.max_bytes = int(self.bytes_per_second * (buffer_duration_ms / 1000.0))

        self._lock = threading.Lock()
        self._buffer = collections.deque()
        self._current_size = 0

    def append(self, chunk: bytes) -> None:
        """Append raw PCM audio bytes to rolling buffer, dropping oldest frames when limit exceeded."""
        if not chunk:
            return

        with self._lock:
            self._buffer.append(chunk)
            self._current_size += len(chunk)

            while self._current_size > self.max_bytes and self._buffer:
                oldest = self._buffer.popleft()
                self._current_size -= len(oldest)

    def get_preroll_bytes(self) -> bytes:
        """Return snapshot of current pre-roll audio bytes in chronological order."""
        with self._lock:
            return b"".join(self._buffer)

    def clear(self) -> None:
        """Flush rolling audio buffer."""
        with self._lock:
            self._buffer.clear()
            self._current_size = 0

    def get_duration_ms(self) -> float:
        """Return total duration of audio currently stored in ring buffer (in ms)."""
        with self._lock:
            return (self._current_size / self.bytes_per_second) * 1000.0
