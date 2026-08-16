# tools/files.py
from __future__ import annotations

from pathlib import Path

class FileManager:
    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace).resolve()

    def _safe(self, path: str) -> Path:
        p_str = str(path).replace("\\", "/")
        if p_str.startswith("/tmp") or p_str.startswith("tmp/"):
            p_rel = p_str.lstrip("/").replace("tmp/", "", 1).lstrip("/")
            p = (self.workspace / "workspace" / "tmp" / p_rel).resolve()
        else:
            p = Path(path)
            if not p.is_absolute():
                p = (self.workspace / path).resolve()
            else:
                p = p.resolve()
        return p

    def read(self, path: str) -> str:
        return self._safe(path).read_text(encoding="utf-8")

    def write(self, path: str, content: str):
        p = self._safe(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def list_dir(self, path: str = ".") -> list:
        return [str(f) for f in self._safe(path).iterdir()]

    def delete(self, path: str):
        self._safe(path).unlink()
