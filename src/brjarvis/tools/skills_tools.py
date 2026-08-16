# tools/skills_tools.py — JARVIS MK37 Skills Tools Plugin
"""
Skills management tools plugin for JARVIS MK37.
Allows querying and running built-in and user custom skills.
"""
from __future__ import annotations

from .registry import register_tool, get_orchestrator_ref


@register_tool(
    name="run_skill",
    description="Execute a named skill (reusable prompt template). Use list_skills to see available skills.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "args": {"type": "string"},
        },
        "required": ["name"],
    }
)
def tool_run_skill(args: dict) -> str:
    from skills import find_skill, load_skills, execute_skill
    skill_name = args.get("name", "").strip()
    skill_args = args.get("args", "")
    
    skill = None
    for s in load_skills():
        if s.name == skill_name:
            skill = s
            break
            
    if skill is None:
        skill = find_skill(skill_name)
        
    if skill is None:
        names = [s.name for s in load_skills()]
        return f"Error: skill '{skill_name}' not found. Available: {', '.join(names)}"
        
    orch = get_orchestrator_ref()
    if orch:
        return execute_skill(skill, skill_args, orch)
    return "Error: orchestrator not initialized for skill execution"


@register_tool(
    name="list_skills",
    description="List all available user-invocable skills.",
    parameters={}
)
def tool_list_skills(args: dict) -> str:
    from skills import load_skills
    skills = [s for s in load_skills() if s.user_invocable]
    if not skills:
        return "No skills available."
        
    lines = ["Available skills:\n"]
    for s in skills:
        triggers = ", ".join(s.triggers)
        hint = f"  args: {s.argument_hint}" if s.argument_hint else ""
        lines.append(f"- **{s.name}** [{triggers}]{hint}\n  {s.description}")
    return "\n".join(lines)
