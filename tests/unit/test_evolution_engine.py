# tests/unit/test_evolution_engine.py — Unit tests for SelfImprovementEngine
"""
Tests for the evolution.engine module — validates that the
SelfImprovementEngine correctly constructs proposals from mocked lesson
and experience data without requiring a live SQLite database.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from brjarvis.evolution.engine import (
    ImprovementProposal,
    SelfImprovementEngine,
    get_evolution_engine,
)


# ── ImprovementProposal Tests ─────────────────────────────────────────────────


class TestImprovementProposal:
    """Unit tests for the ImprovementProposal dataclass."""

    def test_creation_defaults(self):
        proposal = ImprovementProposal(
            topic="test_topic",
            lesson="Do X instead of Y",
            source="lesson",
            confidence=0.85,
            action="Reinforce X pattern",
        )
        assert proposal.topic == "test_topic"
        assert proposal.source == "lesson"
        assert 0.0 <= proposal.confidence <= 1.0
        assert proposal.created_at <= time.time()

    def test_to_dict_roundtrip(self):
        proposal = ImprovementProposal(
            topic="memory",
            lesson="Always check unified memory first",
            source="failure",
            confidence=0.75,
            action="Check memory before LLM call",
            created_at=1234567890.0,
        )
        d = proposal.to_dict()
        assert d["topic"] == "memory"
        assert d["confidence"] == 0.75
        assert d["created_at"] == 1234567890.0
        assert "lesson" in d
        assert "action" in d
        assert "source" in d


# ── SelfImprovementEngine Tests ───────────────────────────────────────────────


class TestSelfImprovementEngine:
    """Unit tests for SelfImprovementEngine with mocked memory subsystem."""

    def _make_engine_with_lessons(self, lessons: list) -> SelfImprovementEngine:
        """Helper: return an engine whose LessonStore returns the given lessons."""
        engine = SelfImprovementEngine.__new__(SelfImprovementEngine)
        mock_store = MagicMock()
        mock_store.list_lessons.return_value = lessons
        engine._lesson_store = mock_store
        return engine

    # -- Smoke tests --

    def test_engine_instantiation_does_not_raise(self):
        """Engine should not raise even if LessonStore is unavailable."""
        with patch(
            "brjarvis.evolution.engine.SelfImprovementEngine._load_lesson_store",
            return_value=None,
        ):
            engine = SelfImprovementEngine()
        assert engine is not None
        assert engine._lesson_store is None

    def test_get_top_lessons_returns_empty_when_no_store(self):
        engine = SelfImprovementEngine.__new__(SelfImprovementEngine)
        engine._lesson_store = None
        result = engine.get_top_lessons()
        assert result == []

    def test_get_top_lessons_sorted_by_weight(self):
        lessons = [
            {"topic": "A", "correction": "fix A", "source": "user", "weight": 1.0},
            {"topic": "B", "correction": "fix B", "source": "user", "weight": 3.5},
            {"topic": "C", "correction": "fix C", "source": "user", "weight": 2.0},
        ]
        engine = self._make_engine_with_lessons(lessons)
        result = engine.get_top_lessons(limit=3)
        assert result[0]["topic"] == "B"  # highest weight first
        assert result[1]["topic"] == "C"

    # -- analyse() --

    def test_analyse_returns_proposals_from_lessons(self):
        lessons = [
            {"topic": "voice", "correction": "Use edge-tts not gtts", "source": "user", "weight": 2.0},
            {"topic": "file", "correction": "Use atomic write pattern", "source": "implicit", "weight": 1.5},
        ]
        engine = self._make_engine_with_lessons(lessons)

        with patch(
            "brjarvis.evolution.engine.SelfImprovementEngine._load_experience_store",
            return_value=None,
        ), patch.object(engine, "_log_cycle"):
            proposals = engine.analyse()

        assert len(proposals) == 2
        topics = {p.topic for p in proposals}
        assert "voice" in topics
        assert "file" in topics

    def test_analyse_skips_low_weight_lessons(self):
        lessons = [
            {"topic": "ignored", "correction": "very weak", "source": "implicit", "weight": 0.1},
            {"topic": "kept", "correction": "strong lesson", "source": "user", "weight": 2.0},
        ]
        engine = self._make_engine_with_lessons(lessons)

        with patch(
            "brjarvis.evolution.engine.SelfImprovementEngine._load_experience_store",
            return_value=None,
        ), patch.object(engine, "_log_cycle"):
            proposals = engine.analyse()

        assert len(proposals) == 1
        assert proposals[0].topic == "kept"

    def test_analyse_skips_empty_correction(self):
        lessons = [
            {"topic": "empty", "correction": "", "source": "user", "weight": 3.0},
        ]
        engine = self._make_engine_with_lessons(lessons)

        with patch(
            "brjarvis.evolution.engine.SelfImprovementEngine._load_experience_store",
            return_value=None,
        ), patch.object(engine, "_log_cycle"):
            proposals = engine.analyse()

        assert proposals == []

    def test_analyse_sorted_by_confidence_descending(self):
        lessons = [
            {"topic": "A", "correction": "fix A", "source": "user", "weight": 1.0},
            {"topic": "B", "correction": "fix B", "source": "user", "weight": 4.5},
        ]
        engine = self._make_engine_with_lessons(lessons)

        with patch(
            "brjarvis.evolution.engine.SelfImprovementEngine._load_experience_store",
            return_value=None,
        ), patch.object(engine, "_log_cycle"):
            proposals = engine.analyse()

        confidences = [p.confidence for p in proposals]
        assert confidences == sorted(confidences, reverse=True)

    # -- propose_improvements() --

    def test_propose_improvements_context_filter(self):
        lessons = [
            {"topic": "voice", "correction": "Use edge-tts", "source": "user", "weight": 2.0},
            {"topic": "memory", "correction": "Always recall context", "source": "user", "weight": 2.0},
        ]
        engine = self._make_engine_with_lessons(lessons)

        with patch(
            "brjarvis.evolution.engine.SelfImprovementEngine._load_experience_store",
            return_value=None,
        ), patch.object(engine, "_log_cycle"):
            proposals = engine.propose_improvements(context="voice")

        # "voice" topic should be ranked first due to relevance boost
        assert proposals[0].topic == "voice"

    def test_propose_improvements_no_context_returns_all(self):
        lessons = [
            {"topic": "X", "correction": "fix X", "source": "user", "weight": 2.0},
            {"topic": "Y", "correction": "fix Y", "source": "user", "weight": 2.0},
        ]
        engine = self._make_engine_with_lessons(lessons)

        with patch(
            "brjarvis.evolution.engine.SelfImprovementEngine._load_experience_store",
            return_value=None,
        ), patch.object(engine, "_log_cycle"):
            proposals = engine.propose_improvements()

        assert len(proposals) == 2

    # -- Singleton factory --

    def test_get_evolution_engine_singleton(self):
        import brjarvis.evolution.engine as mod
        original = mod._engine
        try:
            mod._engine = None
            with patch(
                "brjarvis.evolution.engine.SelfImprovementEngine._load_lesson_store",
                return_value=None,
            ):
                e1 = get_evolution_engine()
                e2 = get_evolution_engine()
            assert e1 is e2
        finally:
            mod._engine = original
