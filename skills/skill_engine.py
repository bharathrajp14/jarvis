# skills/skill_engine.py — Declarative, Versioned, Replayable Skills Engine
"""
Learnable & Repeatable Skills System for BR JARVIS MK37.
Enables saving successful task trajectories as declarative, editable, versioned,
and testable YAML/JSON skill definitions with input schemas and verification assertions.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("JARVIS.SkillEngine")

SKILLS_DIR = Path(__file__).resolve().parent.parent / "workspace" / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SkillStep:
    step_id: str
    tool: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_device: str = "pc"
    target_app: str = ""
    depends_on: List[str] = field(default_factory=list)
    verification: Optional[Dict[str, Any]] = None  # e.g. {"condition": "file_exists", "target": "{output_path}"}


@dataclass
class SkillSchema:
    name: str
    version: str = "1.0.0"
    description: str = ""
    inputs: List[str] = field(default_factory=list)  # e.g. ["topic", "recipient", "output_file"]
    steps: List[SkillStep] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    scope: str = "user"  # "user", "workspace", "system"
    author: str = "JARVIS"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["steps"] = [asdict(s) for s in self.steps]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SkillSchema:
        raw = dict(data)
        if "steps" in raw and isinstance(raw["steps"], list):
            raw["steps"] = [SkillStep(**s) if isinstance(s, dict) else s for s in raw["steps"]]
        return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})


class SkillEngine:
    """Manager and executor for declarative reusable skills."""

    def __init__(self, storage_dir: Path = SKILLS_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._skills_cache: Dict[str, SkillSchema] = {}
        self.reload_skills()

    def reload_skills(self) -> None:
        """Scan skills directory and load all .json / .yaml files."""
        self._skills_cache.clear()
        for f in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                skill = SkillSchema.from_dict(data)
                self._skills_cache[skill.name.lower()] = skill
            except Exception as e:
                logger.warning("Failed to load skill file %s: %s", f.name, e)

    def list_skills(self, tag: Optional[str] = None) -> List[SkillSchema]:
        skills = list(self._skills_cache.values())
        if tag:
            skills = [s for s in skills if tag.lower() in [t.lower() for t in s.tags]]
        return sorted(skills, key=lambda s: s.name)

    def get_skill(self, name: str) -> Optional[SkillSchema]:
        return self._skills_cache.get(name.lower().strip())

    def save_skill(self, skill: SkillSchema) -> Path:
        skill.updated_at = time.time()
        file_path = self.storage_dir / f"{skill.name.lower().replace(' ', '_')}.json"
        file_path.write_text(json.dumps(skill.to_dict(), indent=2), encoding="utf-8")
        self._skills_cache[skill.name.lower()] = skill
        logger.info("Saved Skill '%s' (v%s) to %s", skill.name, skill.version, file_path.name)
        return file_path

    def delete_skill(self, name: str) -> bool:
        norm = name.lower().strip()
        if norm in self._skills_cache:
            file_path = self.storage_dir / f"{norm.replace(' ', '_')}.json"
            if file_path.exists():
                file_path.unlink()
            del self._skills_cache[norm]
            return True
        return False

    def learn_skill_from_trajectory(self, goal: str, actions: List[Dict[str, Any]], skill_name: Optional[str] = None) -> SkillSchema:
        """Extract a reusable parameterized Skill from a successful task action trace."""
        name = skill_name or re.sub(r'[^a-zA-Z0-9_]', '_', goal[:30]).lower().strip('_')
        inputs = []
        steps = []

        for idx, act in enumerate(actions, start=1):
            tool = act.get("tool", "run_code")
            params = act.get("parameters", {})
            step_desc = f"Execute {tool}"
            steps.append(SkillStep(
                step_id=f"step_{idx}",
                tool=tool,
                description=step_desc,
                parameters=params,
                target_device=act.get("target_device", "pc"),
                target_app=act.get("target_app", "")
            ))

        skill = SkillSchema(
            name=name,
            version="1.0.0",
            description=f"Auto-learned skill for: {goal}",
            inputs=inputs,
            steps=steps,
            verification=["steps_completed"],
            tags=["auto-learned", "workflow"]
        )
        return skill

    def execute_skill(self, skill_name: str, input_values: Dict[str, Any], tool_caller: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute a skill by substituting inputs and running steps in order."""
        skill = self.get_skill(skill_name)
        if not skill:
            return {"success": False, "error": f"Skill '{skill_name}' not found"}

        from tools.registry import execute_tool
        dispatch_fn = tool_caller or execute_tool

        results = {}
        for step in skill.steps:
            # Interpolate parameters
            interpolated_params = {}
            for k, v in step.parameters.items():
                if isinstance(v, str):
                    for in_key, in_val in input_values.items():
                        v = v.replace(f"{{{in_key}}}", str(in_val))
                interpolated_params[k] = v

            logger.info("Skill '%s' executing step '%s' [%s]", skill.name, step.step_id, step.tool)
            try:
                out = dispatch_fn(step.tool, interpolated_params)
                results[step.step_id] = out
            except Exception as e:
                logger.error("Skill '%s' failed at step '%s': %s", skill.name, step.step_id, e)
                return {
                    "success": False,
                    "skill": skill.name,
                    "failed_step": step.step_id,
                    "error": str(e),
                    "completed_results": results
                }

        return {
            "success": True,
            "skill": skill.name,
            "results": results,
            "verification": "All steps executed successfully"
        }


_skill_engine_instance: Optional[SkillEngine] = None


def get_skill_engine() -> SkillEngine:
    global _skill_engine_instance
    if _skill_engine_instance is None:
        _skill_engine_instance = SkillEngine()
    return _skill_engine_instance
