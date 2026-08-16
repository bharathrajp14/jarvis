# vision/screen_analyst.py — Screen Capture & Frame Hash Analyst for JARVIS MK37
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
from core.native_bridge import fast_hash

logger = logging.getLogger("JARVIS.ScreenAnalyst")

try:
    from mss import mss
    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False

try:
    from PIL import ImageGrab
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


class ScreenAnalyst:
    """High-speed screen capture analyst with FNV-1a unchanged frame hashing and multi-monitor support."""

    def __init__(self, default_monitor: int = 1):
        self.default_monitor = default_monitor
        self._last_frame_hash: int = 0

    def get_monitors(self) -> List[Dict[str, int]]:
        """List available monitors and their dimensions."""
        if _MSS_AVAILABLE:
            try:
                with mss() as sct:
                    return [
                        {
                            "id": idx,
                            "top": m["top"],
                            "left": m["left"],
                            "width": m["width"],
                            "height": m["height"],
                        }
                        for idx, m in enumerate(sct.monitors)
                    ]
            except Exception as e:
                logger.debug(f"Failed to enumerate monitors with mss: {e}")
        return [{"id": 1, "top": 0, "left": 0, "width": 1920, "height": 1080}]

    def capture_frame(self, monitor_idx: Optional[int] = None) -> Tuple[bytes, int, int, int]:
        """Capture current screen frame from specified or default monitor. Returns (raw_bytes, width, height, frame_hash)."""
        idx = monitor_idx if monitor_idx is not None else self.default_monitor
        width, height = 1920, 1080
        raw_bytes = b""

        if _MSS_AVAILABLE:
            try:
                with mss() as sct:
                    monitors = sct.monitors
                    if 0 <= idx < len(monitors):
                        mon = monitors[idx]
                    else:
                        mon = monitors[1] if len(monitors) > 1 else monitors[0]
                    
                    sct_img = sct.grab(mon)
                    width, height = sct_img.width, sct_img.height
                    raw_bytes = bytes(sct_img.raw)
            except Exception as e:
                logger.debug(f"mss capture failed, falling back to PIL: {e}")

        if not raw_bytes and _PIL_AVAILABLE:
            try:
                img = ImageGrab.grab()
                width, height = img.size
                raw_bytes = img.tobytes()
            except Exception as e:
                logger.debug(f"PIL capture fallback failed: {e}")

        # Compute fast FNV-1a frame hash
        frame_hash = fast_hash(raw_bytes) if raw_bytes else 0
        return raw_bytes, width, height, frame_hash

    def is_frame_unchanged(self, frame_hash: int) -> bool:
        """Check if captured frame is identical to previous frame."""
        if frame_hash != 0 and frame_hash == self._last_frame_hash:
            return True
        self._last_frame_hash = frame_hash
        return False

    def reset_hash(self) -> None:
        """Reset internal frame hash memory."""
        self._last_frame_hash = 0
