# scripts/reformat_skills_library.py — Reformat & Standardize all 362 Skills in library/
"""
Automated Skill Library Transformer for BR JARVIS.
Standardizes YAML frontmatter, category, domain, triggers, BR JARVIS native tool bindings,
argument hints, and invocation criteria for all 362 domain skill files in skills/library/.
"""
import os
import re
import yaml
from pathlib import Path

LIBRARY_DIR = Path(r"d:\BRJARVIS\Br-Jarvis\skills\library")

# Native BR JARVIS Tool Mapping by Category / Domain
DEFAULT_TOOLS_BY_CAT = {
    "engineering-team": ["dev_agent", "code_helper", "repo_controller", "file_processor"],
    "engineering": ["dev_agent", "code_helper", "repo_controller", "file_processor"],
    "c-level-advisor": ["doc_tools", "excel_tools", "web_search", "rag_library"],
    "product-team": ["doc_tools", "excel_tools", "file_processor", "web_search"],
    "marketing-skill": ["web_search", "doc_tools", "file_processor", "browser_control"],
    "marketing": ["web_search", "doc_tools", "file_processor", "browser_control"],
    "finance": ["excel_tools", "doc_tools", "web_search", "file_processor"],
    "productivity": ["calendar_engine", "reminder", "doc_tools", "smart_email_sender"],
    "project-management": ["doc_tools", "excel_tools", "calendar_engine", "web_search"],
    "ra-qm-team": ["doc_tools", "excel_tools", "rag_library", "file_processor"],
    "research": ["web_search", "browser_control", "rag_library", "doc_tools"],
    "research-ops": ["web_search", "browser_control", "rag_library", "excel_tools"],
    "compliance-os": ["doc_tools", "excel_tools", "rag_library", "file_processor"],
    "commercial": ["doc_tools", "excel_tools", "web_search", "smart_email_sender"],
    "business-growth": ["doc_tools", "excel_tools", "web_search", "browser_control"],
    "business-operations": ["doc_tools", "excel_tools", "calendar_engine", "file_processor"],
    "markdown-html": ["doc_tools", "file_processor", "code_helper"],
    "loop-library": ["dev_agent", "code_helper", "doc_tools"]
}

def clean_skill_name(path: Path) -> str:
    """Derive clean skill name from directory or file name."""
    if path.name == "SKILL.md":
        return path.parent.name
    return path.stem

def format_domain(cat_name: str) -> str:
    """Format category name into readable domain string."""
    words = cat_name.replace("-", " ").title().split()
    return " ".join(words)

def generate_triggers(skill_name: str, cat_name: str) -> list[str]:
    """Generate slash command and natural language triggers."""
    cmd = f"/{skill_name.lower().replace('_', '-')}"
    human_trigger = skill_name.replace("-", " ").replace("_", " ").lower()
    return [cmd, f"run {human_trigger}", f"{human_trigger} skill"]

def reformat_skill_file(path: Path) -> bool:
    """Reformat a single skill file with standardized frontmatter."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"[ERROR] Reading {path}: {e}")
        return False

    parts = text.split("---", 2) if text.startswith("---") else ["", "", text]
    
    frontmatter_raw = parts[1].strip() if len(parts) >= 3 else ""
    prompt_body = parts[2].strip() if len(parts) >= 3 else text.strip()

    fm = {}
    if frontmatter_raw:
        try:
            parsed = yaml.safe_load(frontmatter_raw)
            if isinstance(parsed, dict):
                fm = parsed
        except Exception:
            pass

    skill_name = fm.get("name") or clean_skill_name(path)
    description = fm.get("description") or f"BR JARVIS {skill_name} specialized domain skill."
    
    # Infer Category from directory path
    category = fm.get("category", "")
    if not category:
        rel_parts = path.relative_to(LIBRARY_DIR).parts
        category = rel_parts[0] if rel_parts else "general"

    domain = fm.get("domain") or format_domain(category)
    triggers = fm.get("triggers") or generate_triggers(skill_name, category)
    
    # Map tools to native BR JARVIS tools
    existing_tools = fm.get("tools") or fm.get("allowed-tools") or []
    if isinstance(existing_tools, str):
        existing_tools = [t.strip() for t in existing_tools.split(",")]

    jarvis_tools = DEFAULT_TOOLS_BY_CAT.get(category, ["code_helper", "doc_tools", "web_search"])
    
    arg_hint = fm.get("argument-hint") or fm.get("argument_hint") or f"[{skill_name.replace('-', ' ')} details]"
    when_to_use = fm.get("when_to_use") or f"Use when user requests {skill_name.replace('-', ' ')} guidance or task execution."

    new_fm = {
        "name": skill_name,
        "description": str(description).strip(),
        "category": category,
        "domain": domain,
        "triggers": triggers,
        "tools": jarvis_tools,
        "argument-hint": str(arg_hint).strip(),
        "when_to_use": str(when_to_use).strip(),
        "user-invocable": True,
        "context": "inline"
    }

    # Render standardized YAML
    fm_str = yaml.dump(new_fm, sort_keys=False, allow_unicode=True).strip()
    new_content = f"---\n{fm_str}\n---\n\n{prompt_body}\n"

    try:
        path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[ERROR] Writing {path}: {e}")
        return False

def main():
    count = 0
    success = 0
    for root, dirs, files in os.walk(LIBRARY_DIR):
        for f in files:
            if f.endswith(".md"):
                count += 1
                p = Path(root) / f
                if reformat_skill_file(p):
                    success += 1

    print(f"Skill library reformatting complete.")
    print(f"Processed: {count} skill files")
    print(f"Successfully updated: {success} skill files")

if __name__ == "__main__":
    main()
