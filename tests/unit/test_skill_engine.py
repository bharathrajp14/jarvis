"""Unit tests for Skill Engine & Declarative Workflow Loader."""
from __future__ import annotations

import pytest
from brjarvis.skills.skill_engine import SkillEngine, SkillSchema, SkillStep, get_skill_engine


@pytest.mark.unit
def test_skill_engine_initialization():
    """Verify skill engine initializes and can list skills."""
    engine = get_skill_engine()
    assert engine is not None
    skills = engine.list_skills()
    assert isinstance(skills, list)


@pytest.mark.unit
def test_skill_engine_learn_and_save(tmp_path):
    """Verify learning a new skill and persisting to disk."""
    engine = SkillEngine(storage_dir=tmp_path)
    step = SkillStep(step_id="step_1", tool="file_reader", parameters={"path": "test.txt"})
    skill = SkillSchema(name="read_config_skill", description="Read configuration file", steps=[step])
    assert skill.name == "read_config_skill"
    assert len(skill.steps) == 1

    engine.save_skill(skill)
    loaded = engine.get_skill("read_config_skill")
    assert loaded is not None
    assert loaded.name == "read_config_skill"
