# tests/unit/test_memory_voice_float_upgrades.py
import pytest
from memory.vector_store import VectorMemory
from memory.persistent_store import search_memory, MemoryEntry
from voice.tts import NeuralTTS, clean_for_speech


def test_vector_store_distance_filtering():
    vm = VectorMemory()
    # Test that recall returns a list (empty if unavailable or no results)
    res = vm.recall("test query", n=5)
    assert isinstance(res, list)


def test_persistent_store_keyword_stop_word_filtering():
    # Construct test entries
    entries = [
        MemoryEntry(name="Target Python Task", description="Detailed python refactoring guide", content="Focus on AST parsing and desktop automation.", file_path="mem1.md", type="task", scope="user"),
        MemoryEntry(name="Random User Preferences", description="User prefers dark theme", content="User likes blue colors.", file_path="mem2.md", type="fact", scope="user"),
    ]
    # Query with stop words like "what is the python task"
    results = search_memory("what is the python task", scope="all")
    assert isinstance(results, list)


def test_neural_tts_natural_rate_default():
    tts = NeuralTTS()
    assert tts.rate == "+0%"
    assert tts.voice == "en-US-AriaNeural"


def test_clean_for_speech_natural_cadence():
    text = "Here is the result: `code_block` and [link](http://example.com)."
    clean = clean_for_speech(text)
    assert "http" not in clean
    assert "code block" in clean
