from __future__ import annotations

import sys
import threading
import types

from brjarvis.desktop.floating_runtime import FloatingRuntimeAdapter
from brjarvis.desktop.floating_voice import FloatingSpeakerController, FloatingVoiceController


class _Audio:
    def get_wav_data(self):
        return b"RIFF" + b"x" * 200


class _Recognizer:
    def adjust_for_ambient_noise(self, source, duration=0.15):
        return None

    def listen(self, source, timeout=2.0, phrase_time_limit=15.0):
        return _Audio()

    def recognize_google(self, audio):
        return "fallback transcript"


class _Mic:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


class _TTS:
    def __init__(self):
        self.stopped = False
        self.last_text = ""

    @property
    def is_speaking(self):
        return False

    def speak_async(self, text, on_start=None, on_finish=None):
        self.last_text = text
        if on_start:
            on_start()
        if on_finish:
            on_finish()

    def stop(self):
        self.stopped = True


def test_voice_controller_delivers_editable_transcript(monkeypatch):
    monkeypatch.setitem(sys.modules, "speech_recognition", types.SimpleNamespace(Recognizer=_Recognizer))
    states = []
    transcripts = []
    done = threading.Event()
    controller = FloatingVoiceController(
        microphone_factory=_Mic,
        transcriber=lambda wav: "open the workspace",
    )

    controller.start(
        on_state=lambda state, message: states.append((state, message)),
        on_transcript=lambda text: (transcripts.append(text), done.set()),
    )

    assert done.wait(timeout=2)
    assert transcripts == ["open the workspace"]
    assert [state for state, _ in states] == ["recording", "transcribing", "ready"]


def test_speaker_controller_speaks_clean_short_response_and_can_stop():
    tts = _TTS()
    states = []
    speaker = FloatingSpeakerController(tts_factory=lambda: tts)

    assert speaker.speak("Here is **the result** with https://example.com and extra detail.", on_state=lambda s, m: states.append(s))
    assert "example.com" not in tts.last_text
    assert states == ["synthesizing", "speaking", "ready"]
    speaker.stop()
    assert tts.stopped is True


def test_runtime_projects_transcript_speaker_and_workspace_states():
    class _Voice:
        available = True
        recording = False

        def start(self, **kwargs):
            kwargs["on_transcript"]("draft from microphone")

        def stop(self):
            return None

    class _Speaker:
        speaking = False

        def speak(self, text, **kwargs):
            kwargs["on_state"]("speaking", "Speaking…")
            kwargs["on_state"]("ready", "Response ready")
            return True

        def stop(self):
            return None

    class _Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"url": "/web/?handoff=short-lived-token"}

    class _Session:
        def request(self, method, url, **kwargs):
            return _Response()

    adapter = FloatingRuntimeAdapter(voice_controller=_Voice(), speaker_controller=_Speaker(), request_session=_Session())
    adapter.trigger_voice()
    assert adapter.snapshot().transcript == "draft from microphone"
    adapter.update(latest_response="A concise answer.")
    adapter.speak_latest_response()
    assert adapter.snapshot().speaker == "ready"
    ready = threading.Event()
    adapter.request_workspace_handoff(on_ready=lambda url: ready.set())
    assert ready.wait(timeout=2)
    assert adapter.snapshot().workspace == "ready"
    assert "handoff=" in adapter.snapshot().workspace_url



def test_stopped_voice_worker_cannot_emit_late_error(monkeypatch):
    class _BlockingMic:
        def __init__(self):
            self.closed = threading.Event()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.closed.set()

    mic = _BlockingMic()

    class _BlockingRecognizer(_Recognizer):
        def listen(self, source, timeout=2.0, phrase_time_limit=12.0):
            source.closed.wait(timeout=1)
            raise RuntimeError("microphone closed")

    monkeypatch.setitem(sys.modules, "speech_recognition", types.SimpleNamespace(Recognizer=_BlockingRecognizer))
    states = []
    controller = FloatingVoiceController(microphone_factory=lambda: mic, transcriber=lambda wav: "late text")
    controller.start(on_state=lambda state, message: states.append((state, message)))
    for _ in range(100):
        if controller.recording:
            break
        import time

        time.sleep(0.005)
    controller.stop()
    import time

    time.sleep(0.1)
    assert not any(state == "error" for state, _ in states)
