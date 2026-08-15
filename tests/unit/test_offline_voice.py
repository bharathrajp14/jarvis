import pytest
import re
from voice.assistant import BRVoiceAssistant


def test_wake_phrase_detection():
    # Instantiate assistant without UI for testing regex
    assistant = BRVoiceAssistant(ui=None)

    # Valid wake phrases
    assert assistant._is_wake_phrase("jarvis") == True
    assert assistant._is_wake_phrase("hey jarvis") == True
    assert assistant._is_wake_phrase("ok jarvis open notepad") == True
    assert assistant._is_wake_phrase("jarvis refactor python code") == True
    assert assistant._is_wake_phrase("hi jarvis open browser") == True

    # Non-wake phrases & false-positive rejection
    assert assistant._is_wake_phrase("open notepad") == False
    assert assistant._is_wake_phrase("hello world") == False
    assert assistant._is_wake_phrase("travis open browser") == False
    assert assistant._is_wake_phrase("br open browser") == False


def test_command_extraction_from_wake():
    assistant = BRVoiceAssistant(ui=None)

    cmd1 = assistant._extract_command_from_wake("jarvis open youtube")
    assert cmd1.strip() == "open youtube"

    cmd2 = assistant._extract_command_from_wake("hey jarvis create a python script")
    assert cmd2.strip() == "create a python script"

    cmd3 = assistant._extract_command_from_wake("jarvis")
    assert cmd3 == ""
