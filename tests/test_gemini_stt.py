import pytest
from voice.gemini_stt import get_listen_api_key, transcribe_audio_online

def test_get_listen_api_key():
    key = get_listen_api_key()
    assert key != ""
    assert "AQ." in key or len(key) > 10

def test_transcribe_audio_online_fallback_on_invalid():
    # Empty audio should quietly return empty string without error
    result = transcribe_audio_online(b"")
    assert result == ""

def test_transcribe_audio_online_fallback_on_junk_bytes():
    # Corrupt audio data should return empty string and fall back to local engine safely
    result = transcribe_audio_online(b"RTIFF_JUNK_BYTES_TEST", timeout_seconds=1.0)
    assert result == ""
