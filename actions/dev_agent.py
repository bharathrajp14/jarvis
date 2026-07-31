# actions/dev_agent.py — JARVIS MK37 Project Builder (Gemini-Powered)
"""
Builds complete multi-file software projects using Gemini.
- Plans file structure
- Writes all files with dependency awareness
- Installs dependencies
- Opens VSCode
- Runs and auto-fixes errors
"""
from __future__ import annotations

import subprocess
import sys
import json
import re
import time
from pathlib import Path


def _get_gemini():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backends.gemini import GeminiBackend
    return GeminiBackend()


PROJECTS_DIR     = Path.home() / "Desktop" / "JarvisProjects"
MAX_FIX_ATTEMPTS = 4


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()


def _is_error(output: str) -> bool:
    low = output.lower()
    if "timed out" in low: return False
    return any(x in low for x in [
        "traceback", "exception", "error:", "syntaxerror",
        "nameerror", "typeerror", "importerror", "modulenotfounderror",
        "filenotfounderror", "valueerror", "keyerror",
    ])


def _plan_project(description: str, language: str) -> dict:
    gemini = _get_gemini()

    prompt = f"""You are a senior software architect. Create a minimal, complete file plan.

Language: {language}
Project: {description}

Return ONLY valid JSON:
{{
  "project_name": "snake_case_name",
  "entry_point": "main.py",
  "run_command": "python main.py",
  "dependencies": ["requests"],
  "files": [
    {{
      "path": "utils/helpers.py",
      "description": "Helper functions",
      "imports": []
    }},
    {{
      "path": "main.py",
      "description": "Entry point — imports utils.helpers",
      "imports": ["utils.helpers"]
    }}
  ]
}}

Rules:
1. Files must be in DEPENDENCY ORDER — files with no imports first
2. imports[] = other project files this file imports (dot-notation)
3. Keep minimal — only what is truly needed
4. Standard library modules do NOT go in dependencies[]"""

    response = gemini.complete([{"role": "user", "content": prompt}])
    text = re.sub(r"```(?:json)?", "", response).strip().rstrip("`").strip()
    start = text.find("{"); end = text.rfind("}") + 1
    if start != -1:
        text = text[start:end]
    return json.loads(text)


def _write_file(file_info: dict, description: str, all_files: list, language: str,
                project_dir: Path, already_written: dict) -> str:
    gemini = _get_gemini()

    file_path    = file_info["path"]
    file_desc    = file_info.get("description", "")
    file_imports = file_info.get("imports", [])

    # Build context from already-written dependency files
    dep_context = ""
    for dep_dotted in file_imports:
        dep_path = dep_dotted.replace(".", "/") + ".py"
        if dep_path in already_written:
            dep_context += f"\n\n--- {dep_path} (import from this) ---\n{already_written[dep_path][:1500]}"

    files_list = "\n".join(f"  - {f['path']}: {f.get('description', '')}" for f in all_files)

    prompt = (
        f"You are a senior {language} developer writing production-quality code.\n\n"
        f"Project goal: {description}\n\n"
        f"All project files (in order):\n{files_list}\n\n"
        f"{dep_context if dep_context else ''}\n\n"
        f"Write COMPLETE, WORKING code for: {file_path}\n"
        f"Purpose: {file_desc}\n"
        f"{'Imports from: ' + ', '.join(file_imports) if file_imports else 'No project-internal imports.'}\n\n"
        f"Rules:\n"
        f"- Output ONLY raw code. No explanation, no markdown, no backticks.\n"
        f"- Write COMPLETE, RUNNABLE code. No placeholders, no TODOs.\n"
        f"- Use correct import paths matching the file structure.\n"
        f"- Add proper error handling."
    )

    response = gemini.complete([{"role": "user", "content": prompt}])
    code      = _strip_fences(response)

    full_path = project_dir / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(code, encoding="utf-8")
    print(f"[DevAgent] ✅ Written: {file_path} ({len(code)} chars)")
    return code


def _install_dependencies(deps: list, project_dir: Path) -> str:
    if not deps:
        return "No external dependencies."
    to_install = []
    for dep in deps:
        pkg = re.split(r"[>=<!]", dep)[0].strip()
        r = subprocess.run([sys.executable, "-m", "pip", "show", pkg],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            to_install.append(dep)
    if not to_install:
        return "All dependencies already installed."
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install"] + to_install,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120
        )
        return f"Installed: {', '.join(to_install)}"
    except Exception as e:
        return f"Install error (non-fatal): {e}"


def _open_vscode(project_dir: Path):
    for cmd in ["code", "cursor"]:
        try:
            subprocess.Popen([cmd, str(project_dir)], shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
            return
        except Exception:
            continue


def _run_project(run_command: str, project_dir: Path, timeout: int = 30) -> str:
    parts = run_command.split()
    if parts and parts[0].lower() in ("python", "python3"):
        parts[0] = sys.executable
    try:
        result = subprocess.run(
            parts, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, cwd=str(project_dir)
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        parts_out = []
        if stdout: parts_out.append(f"STDOUT:\n{stdout}")
        if stderr: parts_out.append(f"STDERR:\n{stderr}")
        return "\n\n".join(parts_out) if parts_out else "Ran with no output."
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s — long-running app is likely working."
    except Exception as e:
        return f"Run error: {e}"


def _fix_project(error_output: str, description: str, all_files: list,
                 file_codes: dict, language: str, project_dir: Path, entry_point: str) -> dict:
    gemini = _get_gemini()

    # Find the most likely file to fix
    fix_path = entry_point
    for pattern in [r'File ["\']([^"\']+\.py)["\']', r'in ([a-zA-Z_/]+\.py)']:
        m = re.search(pattern, error_output)
        if m:
            candidate = m.group(1).replace("\\", "/")
            if any(candidate in k or k in candidate for k in file_codes):
                for k in file_codes:
                    if candidate in k or k in candidate:
                        fix_path = k
                        break
            break

    current_code = file_codes.get(fix_path, "")
    other_context = ""
    for fp, code in file_codes.items():
        if fp != fix_path:
            other_context += f"\n--- {fp} ---\n{code[:800]}\n"

    prompt = (
        f"Fix this broken {language} file. Output ONLY the fixed code.\n\n"
        f"Project goal: {description}\n\n"
        f"Error:\n{error_output[:2000]}\n\n"
        f"Other files for context:\n{other_context[:2000]}\n\n"
        f"Fix this file ({fix_path}):\n{current_code}"
    )

    response = gemini.complete([{"role": "user", "content": prompt}])
    fixed = _strip_fences(response)

    full_path = project_dir / fix_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(fixed, encoding="utf-8")
    print(f"[DevAgent] 🔧 Fixed: {fix_path}")
    return {fix_path: fixed}


def _auto_install_missing(error: str, project_dir: Path) -> bool:
    m = re.search(r"No module named ['\"]([a-zA-Z0-9_\-.]+)['\"]", error)
    if not m: return False
    pkg = m.group(1).split(".")[0].replace("_", "-")
    print(f"[DevAgent] 📦 Auto-installing: {pkg}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


def dev_agent(parameters: dict, response=None, player=None, session_memory=None, speak=None) -> str:
    p            = parameters or {}
    description  = p.get("description", "").strip()
    language     = p.get("language", "python").strip()
    project_name = p.get("project_name", "").strip()
    timeout      = int(p.get("timeout", 30))

    if not description:
        return "Please describe the project to build."

    def log(msg: str):
        print(f"[DevAgent] {msg}")
        if player: player.write_log(f"[DevAgent] {msg}")

    log("Planning project structure...")
    try:
        plan = _plan_project(description, language)
    except Exception as e:
        return f"Planning failed: {e}"

    proj_name   = project_name or plan.get("project_name", "jarvis_project")
    proj_name   = re.sub(r"[^\w\-]", "_", proj_name)
    project_dir = PROJECTS_DIR / proj_name
    project_dir.mkdir(parents=True, exist_ok=True)

    files        = plan.get("files", [])
    entry_point  = plan.get("entry_point", "main.py")
    run_command  = plan.get("run_command", f"python {entry_point}")
    dependencies = plan.get("dependencies", [])

    log(f"Project: {proj_name} | Files: {len(files)} | Entry: {entry_point}")

    # Sort by dependency count (leaf files first)
    sorted_files = sorted(files, key=lambda f: len(f.get("imports", [])))
    file_codes: dict[str, str] = {}

    for file_info in sorted_files:
        path = file_info.get("path", "")
        if not path: continue
        log(f"Writing {path}...")
        try:
            code = _write_file(file_info, description, files, language, project_dir, file_codes)
            file_codes[path] = code
            time.sleep(0.3)
        except Exception as e:
            log(f"Failed to write {path}: {e}")

    if not file_codes:
        return "Could not write any project files."

    # Install dependencies
    dep_result = _install_dependencies(dependencies, project_dir)
    log(dep_result)

    # Open VSCode
    _open_vscode(project_dir)

    last_output   = ""
    auto_installs = 0

    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        log(f"Running (attempt {attempt}/{MAX_FIX_ATTEMPTS})...")
        last_output = _run_project(run_command, project_dir, timeout)
        log(f"Output: {last_output[:120]}")

        if not _is_error(last_output):
            msg = f"Project '{proj_name}' is working after {attempt} attempt(s). Saved to: {project_dir}"
            if speak: speak(msg)
            return f"{msg}\n\nOutput:\n{last_output}"

        if attempt < MAX_FIX_ATTEMPTS:
            # Try auto-install first
            if "modulenotfounderror" in last_output.lower() and auto_installs < 3:
                if _auto_install_missing(last_output, project_dir):
                    auto_installs += 1
                    log("Dependency installed, retrying...")
                    time.sleep(1)
                    continue

            log("Fixing errors...")
            try:
                updated = _fix_project(last_output, description, files, file_codes, language, project_dir, entry_point)
                file_codes.update(updated)
                time.sleep(1)
            except Exception as e:
                log(f"Fix step failed: {e}")

    msg = f"Built '{proj_name}' but could not fully fix after {MAX_FIX_ATTEMPTS} attempts. Check {project_dir}."
    if speak: speak(msg)
    return f"{msg}\n\nLast error:\n{last_output[:400]}"
