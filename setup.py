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
            version="40.2.0",
            description="BR JARVIS Autonomous AI Operating System",
            py_modules=["brjarvis", "start", "main", "ui_mark", "float_widget", "server"],
            packages=find_packages(),
            entry_points={
                "console_scripts": [
                    "brjarvis=start:main",
                    "jarvis=start:main",
                ],
            },
        )
