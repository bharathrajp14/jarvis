# tests/test_system_upgrades_v4.py — Unit tests for PromptCache, SpeculativeEngine, & SkillHotReloader
from __future__ import annotations

import unittest
from reasoning.prompt_cache import PromptCacheManager
from reasoning.speculative_engine import SpeculativeEngine
from skills.hot_reload import SkillHotReloader


class TestSystemUpgradesV4(unittest.TestCase):

    def test_prompt_cache_manager(self):
        cache = PromptCacheManager(max_cache_entries=10, ttl_seconds=60)
        sys_p = "You are JARVIS AI OS"
        msg_repr = "[user: hello]"
        
        self.assertIsNone(cache.get(sys_p, msg_repr))
        cache.put(sys_p, msg_repr, "Hello Sir, how may I assist you?", token_count=15)
        
        res = cache.get(sys_p, msg_repr)
        self.assertEqual(res, "Hello Sir, how may I assist you?")
        self.assertEqual(cache.tokens_saved, 15)

    def test_speculative_engine(self):
        engine = SpeculativeEngine()
        res_open = engine.speculate_intent("open notepad")
        self.assertIsNotNone(res_open)
        self.assertEqual(res_open[0], "open_app")
        self.assertEqual(res_open[1]["app_name"], "notepad")

        res_none = engine.speculate_intent("write a complex python script for sorting")
        self.assertIsNone(res_none)

    def test_skill_hot_reloader(self):
        reloader = SkillHotReloader()
        skills = reloader.scan_and_reload()
        self.assertIsInstance(skills, list)


if __name__ == "__main__":
    unittest.main()
