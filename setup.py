"""Legacy setuptools shim.

Project metadata and dependencies are authoritative in ``pyproject.toml``.
Use ``python -m pip install -e .`` for development or ``python -m build`` for
release artifacts.
"""
from __future__ import annotations

from setuptools import setup


if __name__ == "__main__":
    setup()
