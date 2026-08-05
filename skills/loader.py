# skills/loader.py
"""
Skill loading: parse markdown files with YAML frontmatter into SkillDef objects.
Adapted from the Claude Code collection's skill system for JARVIS MK37.

Skills can be loaded from:
  - <cwd>/skills/library/  (curated domain skill library)
  - <cwd>/.jarvis/skills/  (project-level, highest priority)
  - ~/.jarvis/skills/       (user-level)
  - Built-in skills         (lowest priority)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


@dataclass
class SkillDef:
    """Definition of a single skill (reusable prompt template)."""
    name: str
    description: str
    triggers: list[str]          # ["/commit", "commit changes"]
    tools: list[str]             # ["Bash", "Read"]  (allowed-tools)
    prompt: str                  # full prompt body after frontmatter
    file_path: str
    # Enhanced fields
    category: str = "general"    # e.g. "engineering", "c-level-advisor", "marketing"
    domain: str = ""             # e.g. "Security", "Code Audit", "Legal"
    when_to_use: str = ""        # when JARVIS should auto-invoke this skill
    argument_hint: str = ""      # e.g. "[branch] [description]"
    arguments: list[str] = field(default_factory=list)  # named arg names
    model: str = ""              # model override
    user_invocable: bool = True  # appears in /skills list
    context: str = "inline"      # "inline" or "fork" (fork = sub-agent)
    source: str = "user"         # "user", "project", "builtin"


# ── Directory paths ────────────────────────────────────────────────────────

def _get_skill_paths() -> list[Path]:
    """Return skill directories ordered from lowest to highest priority."""
    extra_dirs = []
    env_dirs = os.environ.get("JARVIS_SKILLS_DIRS", "")
    if env_dirs:
        extra_dirs = [Path(d.strip()) for d in env_dirs.split(",") if d.strip()]

    pkg_skills = Path(__file__).resolve().parent

    return [
        pkg_skills,                                   # package built-in dir (skills/)
        pkg_skills / "library",                       # domain skills library (skills/library/)
        *extra_dirs,
        Path.home() / ".gemini" / "config" / "skills", # global customization root
        Path.home() / ".jarvis" / "skills",           # user-level
        Path.cwd() / ".agents" / "skills",            # workspace customization root
        Path.cwd() / "skills",                        # project-level skills/
        Path.cwd() / "skills" / "library",            # project-level skills/library/
        Path.cwd() / ".jarvis" / "skills",            # project-level .jarvis/skills/
    ]


# ── List field parser ──────────────────────────────────────────────────────

def _parse_list_field(value: Any) -> list[str]:
    """Parse YAML-like list: ``[a, b, c]``, ``"a, b, c"``, or list object."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    if not isinstance(value, str):
        return []
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [item.strip().strip('"').strip("'") for item in value.split(",") if item.strip()]


# ── Single-file parser ─────────────────────────────────────────────────────

def _parse_skill_file(path: Path, source: str = "user") -> Optional[SkillDef]:
    """Parse a markdown file with ``---`` frontmatter into a SkillDef.

    Frontmatter fields:
        name, description, triggers, tools / allowed-tools,
        when_to_use, argument-hint, arguments, model,
        user-invocable, context, category, domain
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter_raw = parts[1].strip()
    prompt = parts[2].strip()

    fields: dict[str, Any] = {}
    if _HAS_YAML:
        try:
            parsed_yaml = yaml.safe_load(frontmatter_raw)
            if isinstance(parsed_yaml, dict):
                fields = {str(k).lower(): v for k, v in parsed_yaml.items()}
        except Exception:
            pass

    # Fallback to key-value string parsing if PyYAML fails or isn't available
    if not fields:
        for line in frontmatter_raw.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, val = line.partition(":")
            fields[key.strip().lower()] = val.strip()

    name = str(fields.get("name", "")).strip().strip('"\'')
    if not name:
        return None

    # allowed-tools wins over tools if present
    tools_raw = fields.get("allowed-tools", fields.get("tools", ""))
    tools = _parse_list_field(tools_raw)

    triggers_raw = fields.get("triggers", "")
    triggers = _parse_list_field(triggers_raw) if triggers_raw else [f"/{name}"]

    arguments_raw = fields.get("arguments", "")
    arguments = _parse_list_field(arguments_raw)

    user_invocable_raw = str(fields.get("user-invocable", fields.get("user_invocable", "true")))
    user_invocable = user_invocable_raw.lower() not in ("false", "0", "no")

    context = str(fields.get("context", "inline")).strip().lower()
    if context not in ("inline", "fork"):
        context = "inline"

    # Infer category from directory layout if not specified
    category = str(fields.get("category", "")).strip()
    if not category:
        parts_path = path.parts
        if "library" in parts_path:
            idx = parts_path.index("library")
            if idx + 1 < len(parts_path):
                category = parts_path[idx + 1]
    if not category:
        category = "general"

    return SkillDef(
        name=name,
        description=str(fields.get("description", "")).strip(),
        triggers=triggers,
        tools=tools,
        prompt=prompt,
        file_path=str(path),
        category=category,
        domain=str(fields.get("domain", "")).strip(),
        when_to_use=str(fields.get("when_to_use", "")).strip(),
        argument_hint=str(fields.get("argument-hint", fields.get("argument_hint", ""))).strip(),
        arguments=arguments,
        model=str(fields.get("model", "")).strip(),
        user_invocable=user_invocable,
        context=context,
        source=source,
    )


# ── Registry of built-in skills ────────────────────────────────────────────

_BUILTIN_SKILLS: list[SkillDef] = []


def register_builtin_skill(skill: SkillDef) -> None:
    """Register a built-in skill definition."""
    _BUILTIN_SKILLS.append(skill)


# ── Load all skills ────────────────────────────────────────────────────────

def load_skills(include_builtins: bool = True) -> list[SkillDef]:
    """Return skills from disk + builtins, deduplicated (project > user > builtin)."""
    seen: dict[str, SkillDef] = {}

    # Builtins go in first (lowest priority)
    if include_builtins:
        for sk in _BUILTIN_SKILLS:
            seen[sk.name] = sk

    # Scan directories in order (later = higher priority)
    skill_paths = _get_skill_paths()
    pkg_skills_str = str(Path(__file__).resolve().parent)

    for skill_dir in skill_paths:
        if not skill_dir.is_dir():
            continue
        src = "project" if str(skill_dir).startswith(str(Path.cwd())) else ("builtin" if str(skill_dir).startswith(pkg_skills_str) else "user")
        
        # 1. Scan direct *.md files
        for md_file in sorted(skill_dir.glob("*.md")):
            skill = _parse_skill_file(md_file, source=src)
            if skill:
                seen[skill.name] = skill

        # 2. Scan recursive SKILL.md packages (**/*/SKILL.md)
        for skill_md in sorted(skill_dir.rglob("SKILL.md")):
            skill = _parse_skill_file(skill_md, source=src)
            if skill:
                seen[skill.name] = skill

    return list(seen.values())


def find_skill(query: str) -> Optional[SkillDef]:
    """Find a skill whose name or trigger matches the query (case-insensitive)."""
    query = query.strip()
    if not query:
        return None

    q_clean = query.lstrip("/").lower()

    for skill in load_skills():
        s_name = skill.name.lower()
        if q_clean == s_name:
            return skill
        for trigger in skill.triggers:
            t_clean = trigger.lstrip("/").lower()
            if q_clean == t_clean:
                return skill
    return None


# ── Argument substitution ─────────────────────────────────────────────────

def substitute_arguments(prompt: str, args: str, arg_names: list[str]) -> str:
    """Replace $ARGUMENTS (whole args string) and $ARG_NAME placeholders."""
    result = prompt.replace("$ARGUMENTS", args)

    arg_values = args.split()
    for i, arg_name in enumerate(arg_names):
        placeholder = f"${arg_name.upper()}"
        value = arg_values[i] if i < len(arg_values) else ""
        result = result.replace(placeholder, value)

    return result
