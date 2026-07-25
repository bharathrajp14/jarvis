# tests/test_phase4_features.py — Verification unit tests for Semantic File Search & Speculative Model Selector
from __future__ import annotations

import unittest
from tools.file_search_semantic import semantic_file_search, file_search_semantic_action
from reasoning.speculative_selector import SpeculativeModelSelector


class TestPhase4Features(unittest.TestCase):

    def test_semantic_file_search(self):
        res = semantic_file_search("assistant")
        self.assertIsInstance(res, list)

    def test_file_search_semantic_action(self):
        res = file_search_semantic_action({"query": "assistant"})
        self.assertIsInstance(res, str)

    def test_speculative_model_selector(self):
        selector = SpeculativeModelSelector()
        profile, rationale = selector.select_profile("refactor entire architecture and design complex pipeline")
        self.assertEqual(profile, "deep_reasoning")

        profile_fast, _ = selector.select_profile("hi", max_latency_ms=500)
        self.assertEqual(profile_fast, "fast_local")


if __name__ == "__main__":
    unittest.main()
