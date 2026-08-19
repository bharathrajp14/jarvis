# memory/decay.py — Memory Decay & Ebbinghaus Forgetting Engine
"""
Implements Ebbinghaus memory decay:
RetentionScore = Importance * e^(-decay_rate * elapsed_time) * (1 + access_frequency)
Automatically prunes or archives stale memory records and vector embeddings.
"""

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """Memory item with retention metadata."""

    memory_id: str
    content: str
    importance: float = Field(default=1.0, ge=0.1, le=10.0)
    created_at: float = Field(default_factory=time.time)
    last_accessed_at: float = Field(default_factory=time.time)
    access_count: int = 1


class MemoryDecayEngine:
    """
    Evaluates memory retention scores and determines which items should be retained,
    archived, or pruned based on Ebbinghaus forgetting dynamics.
    """

    def __init__(self, half_life_days: float = 7.0, prune_threshold: float = 0.15):
        self.half_life_seconds = half_life_days * 86400.0
        self.decay_rate = math.log(2) / self.half_life_seconds
        self.prune_threshold = prune_threshold

    def calculate_retention(self, item: MemoryItem, current_time: Optional[float] = None) -> float:
        """
        Calculate retention score for a memory item.
        """
        now = current_time or time.time()
        elapsed_seconds = max(0.0, now - item.last_accessed_at)

        # Exponential decay boosted by access frequency
        base_decay = math.exp(-self.decay_rate * elapsed_seconds)
        frequency_boost = 1.0 + math.log(max(1, item.access_count))

        retention = item.importance * base_decay * frequency_boost
        return round(retention, 4)

    def evaluate_batch(self, items: List[MemoryItem]) -> Dict[str, List[MemoryItem]]:
        """
        Partition memory items into 'RETAIN', 'ARCHIVE', and 'PRUNE' categories.
        """
        now = time.time()
        results: Dict[str, List[MemoryItem]] = {"RETAIN": [], "ARCHIVE": [], "PRUNE": []}

        for item in items:
            score = self.calculate_retention(item, current_time=now)
            if score >= 0.5:
                results["RETAIN"].append(item)
            elif score >= self.prune_threshold:
                results["ARCHIVE"].append(item)
            else:
                results["PRUNE"].append(item)

        return results
