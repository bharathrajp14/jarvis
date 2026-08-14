"""BRJARVIS Setup & Package Installer"""
import os
import sys
import subprocess
from setuptools import setup, find_packages

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Running python setup.py directly installs dependencies & editable package
        print("[BRJARVIS] Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=False)
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=False)
        print("\n✅ Setup complete! You can now run 'brjarvis' or 'python start.py'.")
    else:
        setup(
            name="brjarvis",
            version="38.5.0",
            description="BRJARVIS Autonomous AI OS",
            py_modules=["brjarvis", "start", "ui_mark", "float_widget", "server", "main_mk37"],
            packages=find_packages(),
            entry_points={
                "console_scripts": [
                    "brjarvis=brjarvis:main",
                    "jarvis=brjarvis:main",
                ],
            },
        )
