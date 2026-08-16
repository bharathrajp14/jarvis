# context/builder.py — Multi-Source Context Assembler for JARVIS MK37
from __future__ import annotations

import logging
from typing import List, Optional
from .compressor import ContextCompressor
from .token_counter import TokenCounter
from .types import AssembledContext, ContextItem, ContextScope, TokenBudget

logger = logging.getLogger("JARVIS.ContextBuilder")


class ContextBuilder:
    """Builds optimized context payloads within strict token budgets."""

    def __init__(self, budget: Optional[TokenBudget] = None):
        self.budget: TokenBudget = budget or TokenBudget()
        self._items: List[ContextItem] = []
        self.system_prompt: str = "You are JARVIS MK37, an autonomous Local AI Operating System."

    def set_system_prompt(self, prompt: str) -> ContextBuilder:
        self.system_prompt = prompt
        return self

    def add_item(self, item: ContextItem) -> ContextBuilder:
        # Calculate token count if not present
        if item.token_count <= 0:
            item.token_count = TokenCounter.count(item.content)
        self._items.append(item)
        return self

    def add_lessons(self, query: str, priority: int = 6, limit: int = 3) -> ContextBuilder:
        """Retrieve and add relevant lessons learned from past corrections at Priority 6."""
        try:
            from memory.lessons import LessonStore
            ls = LessonStore()
            lessons = ls.get_relevant_lessons(query=query, limit=limit)
            if lessons:
                lines = [f"- {l['topic']}: {l['correction']}" for l in lessons]
                content = "Past User Corrections & Guidelines:\n" + "\n".join(lines)
                item = ContextItem(
                    scope=ContextScope.LESSONS,
                    title="Lessons Learned & User Corrections",
                    content=content,
                    priority=priority,
                )
                self.add_item(item)
        except Exception as e:
            logger.warning(f"Failed to load lessons context: {e}")
        return self

    def add_memories(self, query: str, priority: int = 7, limit: int = 5) -> ContextBuilder:
        """Retrieve and add relevant long-term memories at Priority 7."""
        try:
            from memory.unified_memory import get_unified_memory
            um = get_unified_memory()
            memories = um.recall(query=query, limit=limit)
            if memories:
                lines = [f"- [{m.get('name', 'Memory')}]: {m.get('content', '')}" for m in memories]
                content = "Relevant Long-Term Memories:\n" + "\n".join(lines)
                item = ContextItem(
                    scope=ContextScope.MEMORY,
                    title="Relevant Persistent Memories",
                    content=content,
                    priority=priority,
                )
                self.add_item(item)
        except Exception as e:
            logger.warning(f"Failed to load memory context: {e}")
        return self

    def assemble(self) -> AssembledContext:
        """Assemble items sorted by priority within available token budget."""
        available_budget = self.budget.available_context_tokens
        sys_prompt_tokens = TokenCounter.count(self.system_prompt)
        remaining_budget = max(100, available_budget - sys_prompt_tokens)

        # Sort by priority descending, then timestamp descending
        sorted_items = sorted(self._items, key=lambda x: (x.priority, x.timestamp), reverse=True)

        included_items: List[ContextItem] = []
        context_blocks: List[str] = []
        used_tokens = sys_prompt_tokens

        for item in sorted_items:
            item_tokens = item.token_count
            if used_tokens + item_tokens <= available_budget:
                included_items.append(item)
                context_blocks.append(f"### [{item.scope.value}] {item.title}\n{item.content}")
                used_tokens += item_tokens
            else:
                # Attempt compressing item content to fit remaining budget space
                space_left = available_budget - used_tokens
                if space_left > 150:
                    compressed_content = ContextCompressor.compress(item.content, max_tokens=space_left)
                    comp_tokens = TokenCounter.count(compressed_content)
                    if used_tokens + comp_tokens <= available_budget:
                        item_copy = item.model_copy(update={"content": compressed_content, "token_count": comp_tokens})
                        included_items.append(item_copy)
                        context_blocks.append(f"### [{item_copy.scope.value}] {item_copy.title}\n{compressed_content}")
                        used_tokens += comp_tokens

        assembled_str = "\n\n".join(context_blocks)
        used_pct = (used_tokens / self.budget.max_tokens) * 100.0

        logger.debug(f"Context Assembled: {used_tokens}/{self.budget.max_tokens} tokens ({used_pct:.1f}% budget used)")

        return AssembledContext(
            system_prompt=self.system_prompt,
            context_str=assembled_str,
            items=included_items,
            total_tokens=used_tokens,
            budget=self.budget,
            budget_used_percent=used_pct,
        )
