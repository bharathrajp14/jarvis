from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import re
import sys
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("JARVIS.Actions.ScreenProcessor")

import numpy as np
import sounddevice as sd

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False

from google import genai
from google.genai import types as gtypes

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config_key(key: str, value) -> None:
    try:
        cfg = _load_config()
        cfg[key] = value
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        logger.warning("Could not save config key '%s': %s", key, e)


def _get_api_key() -> str:
    key = _load_config().get("gemini_api_key", "")
    if not key:
        raise RuntimeError("gemini_api_key not found in config.")
    return key


def _get_os() -> str:
    return _load_config().get("os_system", "windows").lower()

_LIVE_MODEL         = "models/gemini-2.5-flash-native-audio-preview-12-2025"
_CHANNELS           = 1
_RECEIVE_SAMPLE_RATE = 24_000
_CHUNK_SIZE         = 1_024

_IMG_MAX_W = 1280
_IMG_MAX_H = 720
_JPEG_Q    = 82

_SYSTEM_PROMPT = (
    "You are JARVIS, Tony Stark's AI assistant. "
    "You are given an image from either the user's screen or their webcam. "
    "Analyze what you see with detail and intelligence. "
    "Describe objects, text, people, components, and their context clearly. "
    "For technical questions (circuits, code, hardware) give specific, expert answers. "
    "Be concise — 2-4 sentences — unless the question demands more detail. "
    "Speak directly to the user ('I can see...', 'You have...'). "
    "Address the user as 'sir' depending on the language they used."
)


def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    if not _PIL:
        return img_bytes, f"image/{source_format.lower()}"

    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning("Image compress failed: %s", e)
        return img_bytes, f"image/{source_format.lower()}"

def _capture_screen() -> tuple[bytes, str]:

    if not _MSS:
        raise RuntimeError("mss is not installed. Run: pip install mss")

    with mss.mss() as sct:
        monitors = sct.monitors          # [0] = all combined, [1..n] = real screens
        target   = monitors[1] if len(monitors) > 1 else monitors[0]
        shot     = sct.grab(target)
        png      = mss.tools.to_png(shot.rgb, shot.size)

    return _compress(png, "PNG")


def _cv2_backend() -> int:
    """Return the best OpenCV camera backend for the current OS."""
    if not _CV2:
        return 0
    os_name = _get_os()
    if os_name == "windows":
        return cv2.CAP_DSHOW    
    if os_name == "mac":
        return cv2.CAP_AVFOUNDATION  
    return cv2.CAP_ANY


def _probe_camera(index: int, backend: int, warmup: int = 5) -> bool:

    if not _CV2:
        return False
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return False
    for _ in range(warmup):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return False
    return bool(np.mean(frame) > 8)


def _detect_camera_index() -> int:

    backend = _cv2_backend()
    logger.info("Auto-detecting camera...")
    for idx in range(6):
        if _probe_camera(idx, backend):
            logger.info("Camera found at index %d", idx)
            _save_config_key("camera_index", idx)
            return idx
        logger.warning("Camera index %d: no usable frame", idx)

    logger.warning("No camera found — defaulting to index 0")
    _save_config_key("camera_index", 0)
    return 0


def _get_camera_index() -> int:
    cfg = _load_config()
    if "camera_index" in cfg:
        return int(cfg["camera_index"])
    return _detect_camera_index()


def _capture_camera() -> tuple[bytes, str]:
    if not _CV2:
        raise RuntimeError("OpenCV (cv2) is not installed. Run: pip install opencv-python")

    index   = _get_camera_index()
    backend = _cv2_backend()
    cap     = cv2.VideoCapture(index, backend)

    if not cap.isOpened():
        raise RuntimeError(f"Camera index {index} could not be opened.")

    for _ in range(10):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Camera returned no frame.")

    if _PIL:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q)
        return buf.getvalue(), "image/jpeg"

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_Q])
    return buf.tobytes(), "image/jpeg"

class _VisionSession:
    def __init__(self):
        self._loop:       Optional[asyncio.AbstractEventLoop] = None
        self._thread:     Optional[threading.Thread]          = None
        self._session                                          = None
        self._out_queue:  Optional[asyncio.Queue]             = None
        self._audio_in:   Optional[asyncio.Queue]             = None
        self._ready_evt:  threading.Event                     = threading.Event()
        self._player                                           = None
        self._lock:       threading.Lock                       = threading.Lock()
        self._started:    bool                                = False

    def start(self, player=None, timeout: float = 25.0) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                if player is not None:
                    self._player = player
                return
            self._player = player
            self._thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True,
                name="VisionSessionThread",
            )
            self._thread.start()

        if not self._ready_evt.wait(timeout=timeout):
            raise RuntimeError(f"Vision session did not connect within {timeout}s.")
        logger.info("Session ready")

    def analyze(self, image_bytes: bytes, mime_type: str, user_text: str) -> None:
        if not self._started:
            logger.warning("Session not started — dropping request")
            return
        asyncio.run_coroutine_threadsafe(
            self._out_queue.put((image_bytes, mime_type, user_text)),
            self._loop,
        )

    def is_ready(self) -> bool:
        return self._session is not None

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._session_loop())

    async def _session_loop(self) -> None:
        self._out_queue = asyncio.Queue(maxsize=30)
        self._audio_in  = asyncio.Queue()

        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"},
        )
        config = gtypes.LiveConnectConfig(
            response_modalities=[gtypes.LiveModality.AUDIO],
            speech_config=gtypes.SpeechConfig(
                voice_config=gtypes.VoiceConfig(
                    prebuilt_voice_config=gtypes.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
        )

        backoff = 2.0
        self._started = True
        while True:
            try:
                logger.info("Connecting...")
                async with client.aio.live.connect(
                    model=_LIVE_MODEL, config=config
                ) as session:
                    self._session = session
                    self._ready_evt.set()
                    backoff = 2.0  
                    logger.info("Connected")

                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self._send_loop())
                        tg.create_task(self._recv_loop())
                        tg.create_task(self._play_loop())

            except* Exception as eg:
                for exc in eg.exceptions:
                    logger.warning("Session error: %s", exc)
            finally:
                self._session = None
                self._ready_evt.clear()

            logger.info("Reconnecting in %.0fs...", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 1.5, 30.0)
            self._ready_evt.set()  

    async def _send_loop(self) -> None:
        while True:
            image_bytes, mime_type, user_text = await self._out_queue.get()
            if not self._session:
                logger.warning("No session — dropping image")
                continue
            try:
                await self._session.send(
                    input=gtypes.Content(
                        parts=[
                            gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                            gtypes.Part.from_text(text=user_text),
                        ]
                    ),
                    end_of_turn=True,
                )
                logger.info("Sent %d bytes — '%s'", len(image_bytes), user_text[:60])
            except Exception as e:
                logger.warning("Send error: %s", e)
                raise  # propagate to TaskGroup → triggers session reconnect

    async def _recv_loop(self) -> None:
        transcript: list[str] = []
        try:
            async for response in self._session.receive():
                if response.data:
                    await self._audio_in.put(response.data)

                sc = response.server_content
                if not sc:
                    continue

                if sc.output_transcription and sc.output_transcription.text:
                    chunk = sc.output_transcription.text.strip()
                    if chunk:
                        transcript.append(chunk)

                if sc.turn_complete:
                    if transcript and self._player:
                        full = re.sub(r"\s+", " ", " ".join(transcript)).strip()
                        if full:
                            self._player.write_log(f"Jarvis: {full}")
                            logger.info("Response: %s", full)
                    transcript = []
                    # Auto-close camera ~2s after JARVIS finishes speaking
                    if self._player and hasattr(self._player, "stop_camera_stream"):
                        async def _deferred_close():
                            await asyncio.sleep(2.0)
                            try:
                                self._player.stop_camera_stream()
                            except Exception:
                                pass
                        asyncio.create_task(_deferred_close())

        except Exception as e:
            logger.warning("Recv error: %s", e)
            raise  

    async def _play_loop(self) -> None:
        stream = sd.RawOutputStream(
            samplerate=_RECEIVE_SAMPLE_RATE,
            channels=_CHANNELS,
            dtype="int16",
            blocksize=_CHUNK_SIZE,
        )
        stream.start()
        try:
            while True:
                chunk = await self._audio_in.get()
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            logger.error("Play error: %s", e)
            raise
        finally:
            stream.stop()
            stream.close()

_session      = _VisionSession()
_session_lock = threading.Lock()
_session_up   = False


def _ensure_session(player=None) -> None:
    global _session_up
    with _session_lock:
        if not _session_up:
            _session.start(player=player)
            _session_up = True
        elif player is not None:
            _session._player = player


def screen_process(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> bool:

    params    = parameters or {}
    user_text = (params.get("text") or params.get("user_text") or "").strip()
    angle     = params.get("angle", "screen").lower().strip()

    if not user_text:
        logger.warning("No question provided — aborting")
        return False

    logger.info("angle=%r  question='%s'", angle, user_text[:80])

    try:
        _ensure_session(player=player)
    except Exception as e:
        logger.error("Could not start session: %s", e)
        return False

    try:
        if angle == "camera":
            image_bytes, mime_type = _capture_camera()
            logger.info("Camera: %d bytes", len(image_bytes))
            if player and hasattr(player, "start_camera_stream"):
                try:
                    player.start_camera_stream()
                except Exception as _e:
                    logger.warning("Camera stream failed: %s", _e)
            elif player and hasattr(player, "show_camera_frame"):
                try:
                    player.show_camera_frame(image_bytes)
                except Exception as _e:
                    logger.warning("Camera preview failed: %s", _e)
        else:
            image_bytes, mime_type = _capture_screen()
            if 'logger' in globals() or 'logger' in locals():
                logger.info(f"{ f"[Vision] 🖥️  Screen: {len(image_bytes):,} bytes" }" if isinstance(f"[Vision] 🖥️  Screen: {len(image_bytes):,} bytes", str) else f"[Vision] 🖥️  Screen: {len(image_bytes):,} bytes")
            else:
                import logging
                logging.getLogger(__name__).info(f"{ f"[Vision] 🖥️  Screen: {len(image_bytes):,} bytes" }" if isinstance(f"[Vision] 🖥️  Screen: {len(image_bytes):,} bytes", str) else f"[Vision] 🖥️  Screen: {len(image_bytes):,} bytes")
    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning(f"{ f"[Vision] ❌ Capture error: {e}" }" if isinstance(f"[Vision] ❌ Capture error: {e}", str) else f"[Vision] ❌ Capture error: {e}")
        else:
            import logging
            logging.getLogger(__name__).warning(f"{ f"[Vision] ❌ Capture error: {e}" }" if isinstance(f"[Vision] ❌ Capture error: {e}", str) else f"[Vision] ❌ Capture error: {e}")
        return False

    _session.analyze(image_bytes, mime_type, user_text)
    return True


def warmup_session(player=None) -> None:
    try:
        _ensure_session(player=player)
    except Exception as e:
        if 'logger' in globals() or 'logger' in locals():
            logger.warning(f"{ f"[Vision] ⚠️  Warmup failed: {e}" }" if isinstance(f"[Vision] ⚠️  Warmup failed: {e}", str) else f"[Vision] ⚠️  Warmup failed: {e}")
        else:
            import logging
            logging.getLogger(__name__).warning(f"{ f"[Vision] ⚠️  Warmup failed: {e}" }" if isinstance(f"[Vision] ⚠️  Warmup failed: {e}", str) else f"[Vision] ⚠️  Warmup failed: {e}")

if __name__ == "__main__":
    if 'logger' in globals() or 'logger' in locals():
        logger.info("[TEST] screen_processor.py")
    else:
        import logging
        logging.getLogger(__name__).info("[TEST] screen_processor.py")
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ "=" * 52 }" if isinstance("=" * 52, str) else "=" * 52)
    else:
        import logging
        logging.getLogger(__name__).info(f"{ "=" * 52 }" if isinstance("=" * 52, str) else "=" * 52)
    mode = input("angle — screen / camera (default: screen): ").strip().lower() or "screen"
    q    = input("Question (Enter = default): ").strip() or "What do you see? Be brief."

    t0 = time.perf_counter()
    warmup_session()
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"Session ready in {time.perf_counter()-t0:.2f}s\n" }" if isinstance(f"Session ready in {time.perf_counter()-t0:.2f}s\n", str) else f"Session ready in {time.perf_counter()-t0:.2f}s\n")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"Session ready in {time.perf_counter()-t0:.2f}s\n" }" if isinstance(f"Session ready in {time.perf_counter()-t0:.2f}s\n", str) else f"Session ready in {time.perf_counter()-t0:.2f}s\n")

    t1 = time.perf_counter()
    ok = screen_process({"angle": mode, "text": q})
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio..." }" if isinstance(f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio...", str) else f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio...")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio..." }" if isinstance(f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio...", str) else f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio...")
    time.sleep(10)
    if 'logger' in globals() or 'logger' in locals():
        logger.warning("Done." if ok else "Failed.")
    else:
        import logging
        logging.getLogger(__name__).warning("Done." if ok else "Failed.")
