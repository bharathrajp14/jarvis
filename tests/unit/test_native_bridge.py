"""Unit tests for Native C Bridge and Pure-Python Fallbacks."""
from __future__ import annotations

import pytest
from brjarvis.core.native_bridge import (
    fast_hash,
    fast_cosine_distance,
    audio_energy,
    grid_transform,
)


@pytest.mark.unit
def test_fnv1a_hashing_consistency():
    """Verify fast non-cryptographic frame hashing produces deterministic output."""
    data = b"BR JARVIS MK40.2 Autonomous Operating Platform"
    h1 = fast_hash(data)
    h2 = fast_hash(data)
    assert h1 == h2
    assert isinstance(h1, int)


@pytest.mark.unit
def test_cosine_distance_calculation():
    """Verify vector distance calculations."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert abs(fast_cosine_distance(v1, v2) - 0.0) < 1e-4
    assert abs(fast_cosine_distance(v1, v3) - 1.0) < 1e-4


@pytest.mark.unit
def test_audio_energy_calculation():
    """Verify RMS audio energy levels calculation."""
    silence = [0.0] * 1024
    energy = audio_energy(silence)
    assert energy == 0.0


@pytest.mark.unit
def test_grid_transform():
    """Verify coordinate normalization transformation."""
    px, py = grid_transform(500, 500, 1920, 1080)
    assert px == 960
    assert py == 540
