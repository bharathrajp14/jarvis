# voice/noise_calibrator.py — BR JARVIS Adaptive Noise Floor Calibrator
"""
AdaptiveNoiseCalibrator: Samples ambient audio at startup and computes
a dynamic RMS baseline that adjusts the VAD detection threshold to the
actual acoustic environment.

Features:
  - 2-second ambient sampling on startup (non-blocking, background thread)
  - Persists calibration to ~/.jarvis/audio_calibration.json for fast restart
  - Classifies environment: QUIET / MODERATE / NOISY
  - Provides live SNR-dB calculation for any audio frame
  - Auto-recalibrates when sustained silence changes noise floor significantly

Usage:
    calibrator = AdaptiveNoiseCalibrator()
    calibrator.start_background_calibration(mic_stream)

    # In your VAD loop:
    threshold = calibrator.get_vad_threshold()
    snr_db = calibrator.get_snr(rms_value)
    env = calibrator.environment_label  # "QUIET" | "MODERATE" | "NOISY"
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("JARVIS.Voice.NoiseCalibrator")

_CALIBRATION_PATH = Path.home() / ".jarvis" / "audio_calibration.json"
_CALIBRATION_SAMPLE_SECONDS = 2.0   # how long to sample ambient audio
_RECALIBRATE_DRIFT_FACTOR = 2.0     # recalibrate if noise floor drifts by 2x
_SPEECH_MULTIPLIER = 3.5            # speech threshold = noise_floor * multiplier


class EnvironmentClass:
    QUIET    = "QUIET"     # RMS < 0.008
    MODERATE = "MODERATE"  # 0.008 <= RMS < 0.025
    NOISY    = "NOISY"     # RMS >= 0.025


class AdaptiveNoiseCalibrator:
    """
    Measures the ambient noise floor and provides dynamic VAD thresholds.

    The calibrator maintains:
      - baseline_rms:   mean RMS of ambient noise (no speech)
      - baseline_zcr:   mean zero-crossing rate of ambient noise
      - environment:    QUIET / MODERATE / NOISY classification
      - vad_threshold:  baseline_rms * SPEECH_MULTIPLIER (capped)

    Thread-safe. Call start_background_calibration() immediately after
    opening the microphone stream.
    """

    def __init__(self):
        self._baseline_rms: float = 0.018    # default fallback threshold
        self._baseline_zcr: float = 0.10
        self._is_calibrated: bool = False
        self._lock = threading.RLock()
        self._calibration_thread: Optional[threading.Thread] = None

        # Rolling statistics for live drift detection
        self._recent_rms_samples: list[float] = []
        self._max_recent_samples = 100  # ~3 seconds at 30ms chunks

        # Load persisted calibration if fresh (< 4 hours old)
        self._try_load_persisted()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_calibrated(self) -> bool:
        return self._is_calibrated

    @property
    def baseline_rms(self) -> float:
        with self._lock:
            return self._baseline_rms

    @property
    def baseline_zcr(self) -> float:
        with self._lock:
            return self._baseline_zcr

    @property
    def environment_label(self) -> str:
        rms = self.baseline_rms
        if rms < 0.008:
            return EnvironmentClass.QUIET
        elif rms < 0.025:
            return EnvironmentClass.MODERATE
        return EnvironmentClass.NOISY

    def get_vad_threshold(self) -> float:
        """
        Get the dynamic RMS threshold above which audio is considered speech.
        Returns baseline_rms * SPEECH_MULTIPLIER, capped between 0.015–0.12.
        """
        with self._lock:
            raw = self._baseline_rms * _SPEECH_MULTIPLIER
            return max(0.015, min(raw, 0.12))

    def get_snr_db(self, frame_rms: float) -> float:
        """
        Compute Signal-to-Noise Ratio in dB for a given audio frame RMS.
        Returns 0.0 if noise floor is zero (avoids log(0)).
        """
        floor = max(self._baseline_rms, 1e-9)
        ratio = max(frame_rms, 1e-9) / floor
        return 20.0 * math.log10(ratio)

    def is_speech(self, frame_rms: float) -> bool:
        """Quick check: is this RMS level above the calibrated speech threshold?"""
        return frame_rms >= self.get_vad_threshold()

    def update_live(self, frame_rms: float) -> None:
        """
        Feed a new RMS sample from a silence frame (call only during known silence).
        Used for online noise floor tracking and drift detection.
        """
        if frame_rms <= 0 or frame_rms > 0.1:
            return  # Ignore outliers
        with self._lock:
            self._recent_rms_samples.append(frame_rms)
            if len(self._recent_rms_samples) > self._max_recent_samples:
                self._recent_rms_samples.pop(0)

            # Check for significant drift (environment changed)
            if len(self._recent_rms_samples) >= 50:
                recent_mean = sum(self._recent_rms_samples[-30:]) / 30
                if (recent_mean > self._baseline_rms * _RECALIBRATE_DRIFT_FACTOR or
                        recent_mean < self._baseline_rms / _RECALIBRATE_DRIFT_FACTOR):
                    old = self._baseline_rms
                    # Smooth update: blend 70% old + 30% new
                    self._baseline_rms = 0.70 * self._baseline_rms + 0.30 * recent_mean
                    logger.info(
                        "NoiseCalibrator: Noise floor updated %.4f → %.4f (%s)",
                        old, self._baseline_rms, self.environment_label
                    )

    # ── Background Calibration ────────────────────────────────────────────────

    def start_background_calibration(
        self,
        mic_stream=None,
        chunk_size: int = 512,
        sample_rate: int = 16000,
    ) -> None:
        """
        Start a background thread that samples ambient audio for 2 seconds
        and computes the noise baseline.

        Args:
            mic_stream: A sounddevice RawInputStream or compatible object.
                        If None, uses a standalone sounddevice stream.
            chunk_size: Audio chunk size in samples.
            sample_rate: Audio sample rate in Hz.
        """
        self._calibration_thread = threading.Thread(
            target=self._run_calibration,
            args=(mic_stream, chunk_size, sample_rate),
            daemon=True,
            name="NoiseCalibrator",
        )
        self._calibration_thread.start()

    def calibrate_sync(
        self,
        chunk_size: int = 512,
        sample_rate: int = 16000,
        duration: float = _CALIBRATION_SAMPLE_SECONDS,
    ) -> float:
        """
        Synchronous calibration (blocking). Samples audio directly.
        Returns the calibrated baseline_rms.
        """
        try:
            import sounddevice as sd
            chunks_needed = int(sample_rate * duration / chunk_size)
            rms_values = []

            logger.info("NoiseCalibrator: Sampling ambient noise for %.1fs...", duration)

            with sd.RawInputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                blocksize=chunk_size,
            ) as stream:
                for _ in range(chunks_needed):
                    data, _ = stream.read(chunk_size)
                    samples = np.frombuffer(bytes(data), dtype=np.int16).astype(np.float32) / 32768.0
                    rms = float(np.sqrt(np.mean(samples ** 2)))
                    if rms > 0:
                        rms_values.append(rms)

            if len(rms_values) >= 5:
                # Use 20th-percentile as noise floor (robust to transient sounds)
                rms_values.sort()
                p20 = rms_values[len(rms_values) // 5]
                with self._lock:
                    self._baseline_rms = p20
                    self._baseline_zcr = self._compute_zcr_baseline(chunk_size, sample_rate)
                    self._is_calibrated = True
                self._persist_calibration()
                env = self.environment_label
                logger.info(
                    "NoiseCalibrator: Baseline RMS=%.4f | Threshold=%.4f | Env=%s",
                    p20, self.get_vad_threshold(), env
                )
                return p20
        except Exception as e:
            logger.warning("NoiseCalibrator: Calibration error: %s", e)

        return self._baseline_rms

    def _run_calibration(self, mic_stream, chunk_size: int, sample_rate: int) -> None:
        """Background thread entry point."""
        time.sleep(0.3)  # Brief delay to allow stream to stabilize
        self.calibrate_sync(chunk_size=chunk_size, sample_rate=sample_rate)

    def _compute_zcr_baseline(self, chunk_size: int, sample_rate: int) -> float:
        """Sample a single frame of silence and compute its ZCR baseline."""
        try:
            import sounddevice as sd
            with sd.RawInputStream(samplerate=sample_rate, channels=1, dtype="int16",
                                    blocksize=chunk_size) as s:
                data, _ = s.read(chunk_size)
                samples = np.frombuffer(bytes(data), dtype=np.int16).astype(np.float32) / 32768.0
                return float(np.sum(np.abs(np.diff(np.signbit(samples)))) / len(samples))
        except Exception:
            return 0.10

    # ── Persistence ───────────────────────────────────────────────────────────

    def _persist_calibration(self) -> None:
        """Save calibration to disk for fast reload on next startup."""
        try:
            _CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "baseline_rms": self._baseline_rms,
                "baseline_zcr": self._baseline_zcr,
                "timestamp": time.time(),
                "environment": self.environment_label,
            }
            _CALIBRATION_PATH.write_text(json.dumps(data, indent=2))
            logger.debug("NoiseCalibrator: Saved to %s", _CALIBRATION_PATH)
        except Exception as e:
            logger.debug("NoiseCalibrator: Persist failed: %s", e)

    def _try_load_persisted(self) -> bool:
        """Load persisted calibration if it's less than 4 hours old."""
        try:
            if not _CALIBRATION_PATH.exists():
                return False
            data = json.loads(_CALIBRATION_PATH.read_text())
            age_hours = (time.time() - data.get("timestamp", 0)) / 3600
            if age_hours > 4.0:
                logger.debug("NoiseCalibrator: Persisted calibration too old (%.1fh)", age_hours)
                return False
            with self._lock:
                self._baseline_rms = float(data.get("baseline_rms", 0.018))
                self._baseline_zcr = float(data.get("baseline_zcr", 0.10))
                self._is_calibrated = True
            logger.info(
                "NoiseCalibrator: Loaded persisted calibration RMS=%.4f Env=%s (%.1fh old)",
                self._baseline_rms, data.get("environment", "?"), age_hours
            )
            return True
        except Exception as e:
            logger.debug("NoiseCalibrator: Load persisted failed: %s", e)
            return False

    def reset(self) -> None:
        """Reset calibration to defaults and delete persisted data."""
        with self._lock:
            self._baseline_rms = 0.018
            self._baseline_zcr = 0.10
            self._is_calibrated = False
            self._recent_rms_samples.clear()
        try:
            _CALIBRATION_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        logger.info("NoiseCalibrator: Reset to defaults")

    def __repr__(self) -> str:
        return (
            f"<AdaptiveNoiseCalibrator calibrated={self._is_calibrated} "
            f"rms={self._baseline_rms:.4f} threshold={self.get_vad_threshold():.4f} "
            f"env={self.environment_label}>"
        )


# ── Module-Level Singleton ────────────────────────────────────────────────────

_calibrator_singleton: Optional[AdaptiveNoiseCalibrator] = None


def get_calibrator() -> AdaptiveNoiseCalibrator:
    """Return or create the global AdaptiveNoiseCalibrator singleton."""
    global _calibrator_singleton
    if _calibrator_singleton is None:
        _calibrator_singleton = AdaptiveNoiseCalibrator()
    return _calibrator_singleton
