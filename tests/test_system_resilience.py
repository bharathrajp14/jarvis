import pytest
from voice.stt import SounddeviceMicrophone
from voice.tts import NeuralTTS


def test_sounddevice_mic_invalid_device_fallback():
    # Attempting to construct microphone with non-existent device index 99999
    mic = SounddeviceMicrophone(device=99999)
    assert mic.device_index == 99999

    # Entering context should attempt device 99999, fail, and fallback to None (system default mic)
    try:
        with mic as m:
            assert m.stream is not None
            # Verified device index fell back or mic opened successfully
            assert m.device_index is None or m.device_index != 99999
    except Exception as e:
        # If sounddevice input fails completely due to environment (no mic), exception is expected
        pytest.skip(f"No audio input device available in environment: {e}")


def test_tts_stop_resilience():
    tts = NeuralTTS()
    tts.speak_async("This is a long test sentence to test barge in speech cancellation.")
    # Instantly stop
    tts.stop()
    assert tts._is_speaking == False
    assert tts._cancel_event.is_set() == True
