# tools/sandbox.py
"""
Code sandbox for JARVIS MK37.
Executes code in a subprocess with timeout protection.
Cross-platform: Windows, Linux, macOS.
"""
from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import os
import platform

logger = logging.getLogger(__name__)

_OS = platform.system()


class CodeSandbox:
    ALLOWED_LANGS = {"python", "javascript", "bash", "powershell"}

    def run(self, code: str, lang: str = "python", timeout: int = 30) -> dict:
        if lang not in self.ALLOWED_LANGS:
            return {"error": f"Language '{lang}' not permitted. Allowed: {', '.join(sorted(self.ALLOWED_LANGS))}"}

        # bash and powershell availability checks
        if lang == "bash" and _OS == "Windows":
            # Try Git Bash or WSL, otherwise fall back to powershell hint
            pass  # still try — Git Bash may be installed
        if lang == "powershell" and _OS != "Windows":
            if not __import__("shutil").which("pwsh"):
                return {"error": "PowerShell (pwsh) is not installed on this system"}

        import re
        code = code.strip()
        code = re.sub(r"^```[a-zA-Z]*\n?", "", code)
        code = re.sub(r"\n?```$", "", code).strip()
        if lang == "python":
            lines = code.split("\n")
            cleaned = []
            narrative = ("let's", "in windows", "here is", "this script", "note:", "we can", "the following", "to get", "using the")
            for line in lines:
                s = line.strip()
                if any(s.lower().startswith(p) for p in narrative):
                    cleaned.append("# " + line)
                else:
                    cleaned.append(line)
            code = "\n".join(cleaned)

        with tempfile.NamedTemporaryFile(
            suffix=self._ext(lang), mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            fname = f.name
        try:
            result = subprocess.run(
                self._cmd(lang, fname),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=timeout,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            return {"stdout": result.stdout, "stderr": result.stderr,
                    "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            return {"error": f"Execution timed out after {timeout}s"}
        except FileNotFoundError as e:
            return {"error": f"Runtime not found for '{lang}': {e}. Is it installed and on PATH?"}
        except Exception as e:
            return {"error": f"Execution error: {e}"}
        finally:
            try:
                os.unlink(fname)
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
    def _ext(self, lang):
        return {
            "python": ".py",
            "javascript": ".js",
            "bash": ".sh",
            "powershell": ".ps1",
        }[lang]

    def _cmd(self, lang, f):
        ps_bin = "powershell" if _OS == "Windows" else "pwsh"
        return {
            "python": [sys.executable, f],       # always use the current Python
            "javascript": ["node", f],
            "bash": ["bash", f],
            "powershell": [ps_bin, "-ExecutionPolicy", "Bypass", "-File", f] if _OS == "Windows" else [ps_bin, "-File", f],
        }[lang]
