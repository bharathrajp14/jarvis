import pytest
from pathlib import Path
from datetime import datetime, timedelta
from actions.background_monitor import add_monitor, remove_monitor, list_monitors
from actions.proactive import ProactiveEngine
from actions.file_processor import file_processor, _detect_type
from actions.reminder import reminder
from memory.memory_manager import save_session_summary, pop_last_session

def test_background_monitor():
    res = add_monitor("Quantum Computing Advances")
    assert "monitoring" in res.lower()
    monitors = list_monitors()
    assert any("Quantum Computing" in m for m in monitors)
    res_rem = remove_monitor("Quantum Computing Advances")
    assert "stopped" in res_rem.lower()

def test_proactive_engine():
    engine = ProactiveEngine(min_silence_secs=1, check_cooldown=1)
    prompt = engine.build_prompt(
        memory={"identity": {"name": "User"}},
        monitors=["Artificial Intelligence"],
        recent_turns=["User: Hello JARVIS", "JARVIS: Hello! How can I assist you?"]
    )
    assert "[PROACTIVE_CHECK]" in prompt
    assert "Artificial Intelligence" in prompt

def test_file_processor_detect_type():
    assert _detect_type(Path("sample.pdf")) == "pdf"
    assert _detect_type(Path("document.docx")) == "docx"
    assert _detect_type(Path("data.csv")) == "csv"
    assert _detect_type(Path("image.png")) == "image"

def test_session_memory_recaps():
    save_session_summary("User researched Mark-L background topic monitoring capabilities.")
    entry = pop_last_session()
    assert entry is not None
    assert "Mark-L background topic monitoring" in entry.get("summary", "")

def test_reminder_tools():
    future_dt = datetime.now() + timedelta(days=1)
    date_str = future_dt.strftime("%Y-%m-%d")
    time_str = "15:00"
    res = reminder({"date": date_str, "time": time_str, "message": "Test reminder"})
    assert "Reminder set" in res or "scheduled" in res.lower()
