# tests/test_claude_skills_integration.py — Integration tests for 360+ Claude Skills Library
from __future__ import annotations

import unittest
from skills.loader import load_skills, find_skill, SkillDef
from skills.registry import get_skills_by_category, search_skills, list_skill_categories


class TestClaudeSkillsIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.skills = load_skills()

    def test_total_skills_count(self):
        """Verify that over 350+ skills are loaded from skills/library/."""
        self.assertGreaterEqual(len(self.skills), 350, f"Expected >= 350 skills, got {len(self.skills)}")

    def test_skill_attributes_validity(self):
        """Ensure all loaded skills have valid non-empty names and descriptions."""
        for skill in self.skills:
            self.assertIsInstance(skill, SkillDef)
            self.assertTrue(bool(skill.name.strip()), "Skill name cannot be empty")
            self.assertIsNotNone(skill.description, "Skill description cannot be None")
            self.assertTrue(bool(skill.category), "Skill category must be set")

    def test_category_grouping(self):
        """Verify skills are grouped across domain categories."""
        categories = list_skill_categories()
        self.assertGreaterEqual(len(categories), 15, "Expected >= 15 skill categories")
        self.assertIn("engineering", categories)
        self.assertIn("c-level-advisor", categories)

    def test_search_skills(self):
        """Verify search query matching across names and categories."""
        engineering_matches = search_skills("code")
        self.assertGreater(len(engineering_matches), 0, "Expected search results for 'code'")

        reviewer = find_skill("code-reviewer")
        self.assertIsNotNone(reviewer, "Expected to find 'code-reviewer' skill")
        if reviewer:
            self.assertEqual(reviewer.name, "code-reviewer")


if __name__ == "__main__":
    unittest.main()
