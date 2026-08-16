# tools/tool_ranker.py — Dynamic Multi-Factor Tool Intelligence & Ranking Subsystem
"""
Multi-factor tool ranking engine for BR JARVIS MK40.
Ensures models receive only the most relevant, safe, and performant top-N tools per turn,
avoiding context bloat, hallucinated schemas, and latency degradation.
"""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("JARVIS.ToolRanker")


@dataclass
class ToolMetadata:
    """Rich semantic and governance metadata for a tool."""
    name: str
    description: str
    category: str = "general"
    capabilities: List[str] = field(default_factory=list)
    risk_level: str = "LOW"  # READ, LOW, MODERATE, HIGH, CRITICAL
    permissions: str = "DEFAULT"
    idempotent: bool = False
    timeout_sec: float = 30.0
    parallelizable: bool = True
    requires_confirmation: bool = False
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionStats:
    """Historical execution and reliability telemetry."""
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.success_count / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls


class ToolRanker:
    """
    Intelligent Dynamic Tool Selector & Ranker.
    Ranks candidates using semantic match, capabilities, historical success, and latency.
    """

    # Core high-priority tools that remain accessible for broad OS autonomy
    CORE_ESSENTIALS = {
        "open_app", "web_search", "file_read", "file_write", "run_code",
        "computer_settings", "window_manager", "system_health"
    }

    def __init__(self):
        self._metadata_registry: Dict[str, ToolMetadata] = {}
        self._stats: Dict[str, ToolExecutionStats] = {}
        self._lock = threading.RLock()

    def register_metadata(self, metadata: ToolMetadata) -> None:
        """Register or update metadata for a tool."""
        with self._lock:
            self._metadata_registry[metadata.name] = metadata
            if metadata.name not in self._stats:
                self._stats[metadata.name] = ToolExecutionStats()

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        with self._lock:
            return self._metadata_registry.get(name)

    def record_execution(self, name: str, success: bool, latency_ms: float) -> None:
        """Record execution outcome to adapt future tool rankings."""
        with self._lock:
            stats = self._stats.setdefault(name, ToolExecutionStats())
            stats.total_calls += 1
            stats.total_latency_ms += latency_ms
            if success:
                stats.success_count += 1
                stats.consecutive_failures = 0
            else:
                stats.failure_count += 1
                stats.consecutive_failures += 1

    def rank_tools(
        self,
        query: str,
        available_tools: Optional[List[ToolMetadata]] = None,
        top_n: int = 8,
        active_permissions: Optional[Set[str]] = None,
    ) -> List[ToolMetadata]:
        """
        Rank and select top-N tools for a given user query.
        """
        with self._lock:
            candidates = available_tools or list(self._metadata_registry.values())
            if not candidates:
                return []

            low_query = query.lower()
            query_tokens = [w for w in re.findall(r'\b\w+\b', low_query) if len(w) >= 2]
            stop_words = {"the", "and", "for", "with", "this", "that", "from", "into", "onto", "about", "your", "what", "how", "can", "you", "please", "all", "our"}
            content_query_words = set(w for w in query_tokens if w not in stop_words)

            scored: List[tuple[float, ToolMetadata]] = []

            for tool in candidates:
                score = 0.0

                # 1. Exact or partial tool name token matching
                tool_name_words = set(re.findall(r'\w+', tool.name.lower()))
                name_overlap = len(tool_name_words.intersection(content_query_words))
                if name_overlap > 0:
                    score += name_overlap * 2.0

                # 2. Capability matching
                for cap in tool.capabilities:
                    cap_words = set(re.findall(r'\w+', cap.lower()))
                    if cap.lower() in low_query or cap_words.intersection(content_query_words):
                        score += 1.5

                # 3. Description semantic keyword overlap
                desc_words = set(w for w in re.findall(r'\b\w+\b', tool.description.lower()) if w not in stop_words)
                desc_overlap = len(desc_words.intersection(content_query_words))
                score += desc_overlap * 0.75

                # 4. Contextual domain hints
                if any(u in low_query for u in ["http://", "https://", "www.", ".com", ".org", "url"]) and "web" in tool.capabilities:
                    score += 1.5

                if any(k in low_query for k in ["commit", "branch", "repo", "push", "diff", "checkout"]) and tool.name == "git_repo_tool":
                    score += 2.5

                if any(k in low_query for k in ["xlsx", "csv", "spreadsheet", "revenue", "formula", "rows", "columns"]) and tool.name == "excel_analyze":
                    score += 2.5

                if any(k in low_query for k in ["pdf", "invoice.pdf", "contract"]) and tool.name == "pdf_tools":
                    score += 2.5

                if any(k in low_query for k in ["remind", "reminder", "alarm", "notify", "standup"]) and tool.name == "reminder":
                    score += 2.5

                if any(k in low_query for k in ["book", "manual", "guide", "multi-volume", "documentation"]) and tool.name == "longform_builder":
                    score += 2.0

                if any(k in low_query for k in ["semantic", "authentication", "payment", "meaning"]) and tool.name == "file_search_semantic":
                    score += 2.0

                # 5. Historical Telemetry Accounting
                stats = self._stats.get(tool.name)
                if stats:
                    score += stats.success_rate * 0.4
                    score -= stats.consecutive_failures * 0.3
                    if stats.avg_latency_ms > 3000:
                        score -= 0.2

                # 6. Risk penalty for CRITICAL unless prompted
                if tool.risk_level == "CRITICAL" and not any(w in low_query for w in ["delete", "remove", "drop", "kill", "format"]):
                    score -= 0.5

                scored.append((score, tool))

            # Sort descending by score
            scored.sort(key=lambda x: x[0], reverse=True)
            return [t for _, t in scored[:top_n]]


_global_tool_ranker: Optional[ToolRanker] = None


def get_tool_ranker() -> ToolRanker:
    """Retrieve global ToolRanker singleton."""
    global _global_tool_ranker
    if _global_tool_ranker is None:
        _global_tool_ranker = ToolRanker()
        try:
            from tools.registry import TOOL_SCHEMAS
            for s in TOOL_SCHEMAS:
                _global_tool_ranker.register_metadata(ToolMetadata(
                    name=s.get("name", ""),
                    description=s.get("description", ""),
                    capabilities=s.get("name", "").split("_"),
                    input_schema=s.get("parameters", {}),
                ))
        except Exception:
            pass
    return _global_tool_ranker
