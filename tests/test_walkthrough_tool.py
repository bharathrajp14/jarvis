import os
from pathlib import Path
from tools.doc_tools import generate_walkthrough


def test_generate_walkthrough_tool():
    args = {
        "title": "Test Walkthrough Generation",
        "summary": "Verified automated creation of GitHub-flavored markdown walkthroughs.",
        "changes": "- Created `tools/doc_tools.py` `generate_walkthrough` tool handler.\n- Registered `/walkthrough` skill in `skills/builtin_writer.py`.",
        "verification": "All 81 tests passing.",
        "filename": "test_generated_walkthrough.md"
    }

    res = generate_walkthrough(args)
    assert "Generated Walkthrough document successfully" in res

    file_path = Path(__file__).resolve().parent.parent / "test_generated_walkthrough.md"
    assert file_path.exists()
    
    content = file_path.read_text(encoding="utf-8")
    assert "# Walkthrough — Test Walkthrough Generation" in content
    assert "Verified automated creation of GitHub-flavored markdown walkthroughs." in content
    assert "All 81 tests passing." in content

    # Clean up test file
    file_path.unlink(missing_ok=True)
