import pytest
import sys
from pathlib import Path

def test_ui_mark_importable():
    # Verify ui_mark module can be imported cleanly
    import ui_mark
    assert hasattr(ui_mark, "JarvisUI")
    assert hasattr(ui_mark, "apply_ui_accent")
    assert hasattr(ui_mark, "current_palette")

def test_ui_mark_palette():
    import ui_mark
    pal = ui_mark.current_palette()
    assert isinstance(pal, dict)
    assert "PRI" in pal
    assert "BG" in pal
