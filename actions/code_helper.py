# actions/code_helper.py — JARVIS MK37 Code Assistant (Gemini-Powered)
"""
AI-powered code helper using Gemini.
Actions: write, edit, explain, run, build, optimize, screen_debug, auto
"""
from __future__ import annotations

import subprocess
import sys
import re
import time
from pathlib import Path


def _get_gemini():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gemini_backend import GeminiBackend
    return GeminiBackend()


DESKTOP         = Path.home() / "Desktop"
MAX_BUILD_TRIES = 3


def _clean_code(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text).strip()
    lines = text.split("\n")
    cleaned = []
    narrative_prefixes = ("let's", "in windows", "here is", "this script", "note:", "we can", "the following", "to get", "using the")
    for line in lines:
        s = line.strip()
        if any(s.lower().startswith(p) for p in narrative_prefixes):
            cleaned.append("# " + line)
        else:
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def _resolve_save_path(output_path: str, language: str) -> Path:
    ext_map = {
        "python": ".py", "py": ".py", "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts", "html": ".html", "css": ".css",
        "java": ".java", "cpp": ".cpp", "c": ".c", "bash": ".sh",
        "shell": ".sh", "powershell": ".ps1", "sql": ".sql",
        "json": ".json", "rust": ".rs", "go": ".go",
    }
    if output_path:
        p = Path(output_path)
        return p if p.is_absolute() else DESKTOP / p
    ext = ext_map.get((language or "python").lower(), ".py")
    return DESKTOP / f"jarvis_code{ext}"


def _normalize_path(file_path: str | Path | None) -> Path:
    if not file_path:
        return Path()
    p_str = str(file_path).replace("\\", "/")
    if p_str.startswith("/tmp/") or p_str.startswith("tmp/"):
        rel = p_str.lstrip("/")
        if rel.startswith("tmp/"):
            rel = rel[4:]
        ws = Path(__file__).resolve().parent.parent / "workspace" / "tmp"
        ws.mkdir(parents=True, exist_ok=True)
        return ws / rel
    return Path(file_path)


def _read_file(file_path: str) -> tuple[str, str]:
    if not file_path:
        return "", "No file path provided."
    p = _normalize_path(file_path)
    if not p.exists():
        return "", f"File not found: {file_path}"
    try:
        return p.read_text(encoding="utf-8"), ""
    except Exception as e:
        return "", f"Could not read file: {e}"


def _save_file(path: Path, content: str) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Saved to: {path}"
    except Exception as e:
        return f"Could not save: {e}"


def _has_error(output: str) -> bool:
    signals = ["error", "exception", "traceback", "syntaxerror",
               "nameerror", "typeerror", "stderr", "failed", "crash"]
    return any(s in output.lower() for s in signals)


def _run_file(path: Path, args: list, timeout: int) -> str:
    interpreters = {
        ".py":  [sys.executable], ".js": ["node"], ".ts": ["ts-node"],
        ".sh":  ["bash"], ".ps1": ["powershell", "-File"],
    }
    interp = interpreters.get(path.suffix.lower())
    if not interp:
        return f"No interpreter for {path.suffix}."
    try:
        result = subprocess.run(
            interp + [str(path)] + (args or []),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, cwd=str(path.parent)
        )
        parts = []
        if result.stdout.strip(): parts.append(f"Output:\n{result.stdout.strip()}")
        if result.stderr.strip(): parts.append(f"Stderr:\n{result.stderr.strip()}")
        return "\n\n".join(parts) if parts else "Executed with no output."
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s."
    except FileNotFoundError:
        return f"Interpreter not found: {interp[0]}"
    except Exception as e:
        return f"Execution error: {e}"


def _write_code(description: str, language: str, output_path: str) -> tuple[str, Path]:
    gemini = _get_gemini()
    lang   = language or "python"

    prompt = (
        f"You are an expert {lang} developer.\n"
        f"Write clean, working, well-commented {lang} code for:\n\n{description}\n\n"
        "Rules:\n"
        "- Output ONLY the code. No explanation, no markdown, no backticks.\n"
        "- Add helpful inline comments.\n"
        "- Handle errors and edge cases.\n"
        "- Use modern best practices."
    )
    response = gemini.complete([{"role": "user", "content": prompt}])
    code     = _clean_code(response)
    path     = _resolve_save_path(output_path, lang)
    _save_file(path, code)
    return code, path


def _fix_code(code: str, error_output: str, description: str) -> str:
    gemini = _get_gemini()
    prompt = (
        f"You are an expert debugger. Fix this broken code.\n"
        f"Return ONLY the corrected code — no explanation, no markdown.\n\n"
        f"Goal: {description}\n\nError:\n{error_output[:2000]}\n\nBroken code:\n{code}"
    )
    return _clean_code(gemini.complete([{"role": "user", "content": prompt}]))


def code_helper(parameters: dict, response=None, player=None, session_memory=None, speak=None) -> str:
    p           = parameters or {}
    action      = p.get("action", "auto").lower().strip()
    description = p.get("description", "").strip()
    language    = p.get("language", "python").strip()
    output_path = p.get("output_path", "").strip()
    file_path   = p.get("file_path", "").strip()
    code        = p.get("code", "").strip()
    args        = p.get("args", [])
    timeout     = int(p.get("timeout", 30))

    if action == "auto":
        desc_l = description.lower()
        if any(k in desc_l for k in ["explain", "what does", "analyze"]):
            action = "explain"
        elif any(k in desc_l for k in ["optimize", "refactor", "improve"]) and (code or file_path):
            action = "optimize"
        elif file_path and Path(file_path).exists() and any(k in desc_l for k in ["edit", "update", "fix", "change"]):
            action = "edit"
        elif file_path and Path(file_path).exists() and any(k in desc_l for k in ["run", "execute"]):
            action = "run"
        elif any(k in desc_l for k in ["build", "create and run", "make it work"]):
            action = "build"
        else:
            action = "write"

    if action == "write":
        if not description:
            return "Please describe what to write."
        if player: player.write_log("[Code] Writing...")
        try:
            code_out, path = _write_code(description, language, output_path)
            return f"Code written. Saved to: {path}\n\nPreview:\n{chr(10).join(code_out.splitlines()[:10])}"
        except Exception as e:
            return f"Could not generate code: {e}"

    elif action == "edit":
        if not file_path:
            return "Please provide a file path to edit."
        content, err = _read_file(file_path)
        if err: return err
        if player: player.write_log("[Code] Editing...")
        gemini = _get_gemini()
        prompt = (
            f"Apply this change to the code. Return ONLY the complete updated code.\n\n"
            f"Change: {description or p.get('instruction', '')}\n\nCode:\n{content}"
        )
        try:
            edited = _clean_code(gemini.complete([{"role": "user", "content": prompt}]))
            _save_file(Path(file_path), edited)
            return f"File edited: {file_path}"
        except Exception as e:
            return f"Edit failed: {e}"

    elif action == "explain":
        if file_path and not code:
            code, err = _read_file(file_path)
            if err: return err
        if not code:
            return "Please provide code or a file path."
        gemini = _get_gemini()
        prompt = f"Explain this code clearly in 3-5 sentences:\n\n{code[:4000]}"
        return gemini.complete([{"role": "user", "content": prompt}])

    elif action in ("run", "run_code", "execute"):
        if not file_path and code:
            tmp_path = _normalize_path("/tmp/temp_inline_code.py")
            _save_file(tmp_path, code)
            return _run_file(tmp_path, args, timeout)
        if not file_path and description:
            # Generate code from description and run
            code_str, tmp_path = _write_code(description, language or "python", "")
            return _run_file(tmp_path, args, timeout)
        if not file_path:
            return "Please provide a file path or code to run."
        p_path = _normalize_path(file_path)
        if not p_path.exists():
            return f"File not found: {file_path}"
        return _run_file(p_path, args, timeout)

    elif action == "optimize":
        if file_path and not code:
            code, err = _read_file(file_path)
            if err: return err
        if not code:
            return "Please provide code to optimize."
        gemini = _get_gemini()
        prompt = (
            f"Optimize this {language} code for performance, readability, and best practices.\n"
            "Return ONLY the optimized code — no explanation.\n\n"
            f"Code:\n{code[:6000]}"
        )
        optimized = _clean_code(gemini.complete([{"role": "user", "content": prompt}]))
        save_path = Path(file_path) if file_path else _resolve_save_path(output_path, language)
        _save_file(save_path, optimized)
        return f"Code optimized. Saved to: {save_path}"

    elif action == "build":
        if not description:
            return "Please describe what to build."
        if player: player.write_log("[Code] Building...")

        try:
            code_str, path = _write_code(description, language, output_path)
        except Exception as e:
            return f"Could not write code: {e}"

        last_output = ""
        for attempt in range(1, MAX_BUILD_TRIES + 1):
            if player: player.write_log(f"[Code] Attempt {attempt}...")
            last_output = _run_file(path, args, timeout)
            if not _has_error(last_output):
                msg = f"Build complete in {attempt} attempt(s). Saved to {path}."
                if speak: speak(msg)
                return f"{msg}\n\nOutput:\n{last_output}"
            print(f"[Code] Error on attempt {attempt}, fixing...")
            try:
                code_str = _fix_code(code_str, last_output, description)
                _save_file(path, code_str)
            except Exception as e:
                return f"Fix failed: {e}"

        return f"Could not build after {MAX_BUILD_TRIES} attempts.\nLast error: {last_output[:300]}\nSaved to: {path}"

    elif action == "screen_debug":
        try:
            import pyautogui, io
            screenshot_path = Path.home() / "Desktop" / f"debug_{int(time.time())}.png"
            img = pyautogui.screenshot()
            img.save(str(screenshot_path))
            img_bytes = screenshot_path.read_bytes()
            gemini = _get_gemini()
            analysis = gemini.complete_with_vision(
                image_bytes=img_bytes,
                mime_type="image/png",
                prompt=f"Analyze this screenshot for errors. User question: {description or 'What errors do you see?'}\nProvide specific fixes."
            )
            screenshot_path.unlink(missing_ok=True)
            return analysis
        except Exception as e:
            return f"Screen debug failed: {e}"

    else:
        return f"Unknown action: '{action}'. Use write, edit, explain, run, build, optimize, screen_debug."
