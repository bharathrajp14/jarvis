# tests/test_ui_mark.py — Test for ui_mark.py Desktop UI
from __future__ import annotations

import unittest
import sys
from pathlib import Path

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestUIMark(unittest.TestCase):
    def test_ui_mark_import(self):
        import ui_mark
        self.assertTrue(hasattr(ui_mark, "MainWindow"))
        self.assertTrue(hasattr(ui_mark, "JarvisUI"))
        self.assertTrue(hasattr(ui_mark, "run_voice_ui"))

    def test_ui_palette(self):
        import ui_mark
        palette = ui_mark.current_palette()
        self.assertIn("PRI", palette)
        self.assertIn("BG", palette)


if __name__ == "__main__":
    unittest.main()
