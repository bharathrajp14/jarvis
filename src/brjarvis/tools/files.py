# tools/files.py
from __future__ import annotations

from pathlib import Path
from brjarvis.core.paths import paths

class FileManager:
    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or paths.WORKSPACE_ROOT).resolve()

    def _safe(self, path: str | Path) -> Path:
        p_str = str(path).replace("\\", "/")
        if p_str.startswith("/tmp") or p_str.startswith("tmp/"):
            p_rel = p_str.lstrip("/").replace("tmp/", "", 1).lstrip("/")
            p = (paths.TEMP_ROOT / p_rel).resolve()
        else:
            p = Path(path)
            if not p.is_absolute():
                # Guard against double-workspace paths like "workspace/Portfolio"
                # when self.workspace already ends in "workspace". Strip any
                # leading "workspace/" prefix (case-insensitive) before joining.
                ws_name = self.workspace.name  # e.g. "workspace"
                parts = p.parts
                if parts and parts[0].lower() == ws_name.lower():
                    p = Path(*parts[1:]) if len(parts) > 1 else Path(".")
                p = (self.workspace / p).resolve()
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
