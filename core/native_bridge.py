# core/native_bridge.py — BR JARVIS MK37 Native C Extension Bridge
"""
High-performance C/C++ native bridge for JARVIS MK37.
Provides fast FNV-1a hashing, C-level audio VAD energy calculation,
fast cosine vector distance calculations, and low-overhead system metrics.
Includes pure-Python fallbacks when compiled native binary is unavailable.
"""
from __future__ import annotations

import logging
import ctypes
import hashlib
import math
import os
import platform
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR   = Path(__file__).resolve().parent.parent
NATIVE_DIR = BASE_DIR / "native"

system = platform.system()
if system == "Windows":
    LIB_NAME = "jarvis_native.dll"
elif system == "Darwin":
    LIB_NAME = "libjarvis_native.dylib"
else:
    LIB_NAME = "libjarvis_native.so"

LIB_PATH = NATIVE_DIR / LIB_NAME

_c_lib: ctypes.CDLL | None = None
_native_loaded: bool       = False
_native_version: str       = "Python Fallback"
_compile_attempted: bool   = False


def _init_native():
    global _c_lib, _native_loaded, _native_version, _compile_attempted
    if _native_loaded:
        return

    if not LIB_PATH.exists() and not _compile_attempted:
        _compile_attempted = True
        try:
            from scripts.setup_native import compile_native
            compile_native()
        except Exception:
            try:
                from setup_native import compile_native
                compile_native()
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
    if LIB_PATH.exists():
        try:
            _c_lib = ctypes.CDLL(str(LIB_PATH))
            
            # Signatures
            _c_lib.jarvis_fast_hash.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
            _c_lib.jarvis_fast_hash.restype  = ctypes.c_uint64

            _c_lib.jarvis_audio_energy.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.c_size_t]
            _c_lib.jarvis_audio_energy.restype  = ctypes.c_float

            if hasattr(_c_lib, "jarvis_vector_dot_product"):
                _c_lib.jarvis_vector_dot_product.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_size_t]
                _c_lib.jarvis_vector_dot_product.restype  = ctypes.c_float

            if hasattr(_c_lib, "jarvis_fast_cosine_distance"):
                _c_lib.jarvis_fast_cosine_distance.argtypes = [ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_size_t]
                _c_lib.jarvis_fast_cosine_distance.restype  = ctypes.c_float

            _c_lib.jarvis_grid_transform.argtypes = [
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
            ]
            _c_lib.jarvis_grid_transform.restype = None

            _c_lib.jarvis_sys_memory_avail_kb.argtypes = []
            _c_lib.jarvis_sys_memory_avail_kb.restype  = ctypes.c_uint64

            _c_lib.jarvis_native_version.argtypes = []
            _c_lib.jarvis_native_version.restype  = ctypes.c_char_p

            _native_loaded  = True
            _native_version = _c_lib.jarvis_native_version().decode("utf-8")
            logger.info(f"[NativeBridge] ⚡ Loaded C Native Library v{_native_version}")
        except Exception as e:
            logger.warning(f"[NativeBridge] ⚠️ Failed to load C native library: {e}")
            _c_lib = None
            _native_loaded = False


# Auto init on module import
_init_native()


def is_native_active() -> bool:
    return _native_loaded


def get_status() -> dict:
    return {
        "active": _native_loaded,
        "version": _native_version,
        "library_path": str(LIB_PATH),
    }


def fast_hash(data: bytes) -> int:
    """Fast non-cryptographic FNV-1a 64-bit frame hashing."""
    if not data:
        return 0
    if _native_loaded and _c_lib:
        try:
            buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
            return _c_lib.jarvis_fast_hash(buf, len(data))
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    return int(hashlib.md5(data).hexdigest()[:16], 16)


def fast_cosine_distance(v1: list[float], v2: list[float]) -> float:
    """Calculate fast cosine distance (1.0 - cosine_similarity)."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 1.0
    if _native_loaded and _c_lib and hasattr(_c_lib, "jarvis_fast_cosine_distance"):
        try:
            dim = len(v1)
            arr1 = (ctypes.c_float * dim)(*v1)
            arr2 = (ctypes.c_float * dim)(*v2)
            return float(_c_lib.jarvis_fast_cosine_distance(arr1, arr2, dim))
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    # Pure Python fallback
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 <= 0 or norm2 <= 0:
        return 1.0
    sim = dot / (norm1 * norm2)
    return max(0.0, 1.0 - sim)


def audio_energy(samples: list[float] | tuple[float, ...]) -> float:
    """Calculate RMS audio energy for Voice Activity Detection."""
    if not samples:
        return 0.0
    if _native_loaded and _c_lib:
        try:
            c_arr = (ctypes.c_float * len(samples))(*samples)
            return float(_c_lib.jarvis_audio_energy(c_arr, len(samples)))
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    try:
        sum_sq = sum(s * s for s in samples)
        return math.sqrt(sum_sq / len(samples))
    except OverflowError:
        max_val = max(abs(s) for s in samples)
        if max_val == 0.0:
            return 0.0
        scaled_samples = [s / max_val for s in samples]
        sum_sq_scaled = sum(s * s for s in scaled_samples)
        return max_val * math.sqrt(sum_sq_scaled / len(samples))


def grid_transform(x_norm: int, y_norm: int, screen_w: int, screen_h: int) -> tuple[int, int]:
    """Transform 0..1000 normalized target grid coordinates to actual screen pixels."""
    if _native_loaded and _c_lib:
        try:
            out_x = ctypes.c_int()
            out_y = ctypes.c_int()
            _c_lib.jarvis_grid_transform(x_norm, y_norm, screen_w, screen_h, ctypes.byref(out_x), ctypes.byref(out_y))
            return out_x.value, out_y.value
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    px = int((float(x_norm) / 1000.0) * float(screen_w))
    py = int((float(y_norm) / 1000.0) * float(screen_h))
    px = max(0, min(screen_w - 1, px)) if screen_w > 0 else 0
    py = max(0, min(screen_h - 1, py)) if screen_h > 0 else 0
    return px, py


def get_sys_memory_avail_kb() -> int:
    """Retrieve available memory in KB using low-overhead C call on Linux."""
    if _native_loaded and _c_lib:
        try:
            val = _c_lib.jarvis_sys_memory_avail_kb()
            if val > 0:
                return val
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
    try:
        import psutil
        return int(psutil.virtual_memory().available / 1024)
    except Exception:
        return 0


def proc_memory_kb(pid: int = 0) -> int:
    """Retrieve process memory usage in KB."""
    try:
        import os
        import psutil
        target_pid = pid if pid > 0 else os.getpid()
        proc = psutil.Process(target_pid)
        return int(proc.memory_info().rss / 1024)
    except Exception:
        return get_sys_memory_avail_kb()

