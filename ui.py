"""
Shim for missing ui.py file, redirecting to ui_mark.py
"""
import sys
import os

# Redirect imports
try:
    from ui_mark import JarvisUI, run_voice_ui
except ImportError:
    pass

