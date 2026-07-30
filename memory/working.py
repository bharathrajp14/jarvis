# memory/working.py — JARVIS MK37 Working Memory (Fixed)

class WorkingMemory:
    def __init__(self, max_tokens: int = 100_000):
        self.history: list[dict] = []
        self.max_tokens = max_tokens
        self._char_count = 0  # Running character count for O(1) trim checks

    @property
    def messages(self) -> list[dict]:
        """Alias for self.history — backwards compatibility with orchestrator.py."""
        return self.history

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self._char_count += len(content)
        self._trim()

    def _trim(self):
        """Trim history to stay within token budget. O(n) instead of O(n²)."""
        if not self.history:
            return

        if self._char_count / 4 <= self.max_tokens:
            return

        root_msg = self.history[0]
        # Pop non-root turns (index 1) first to satisfy token budget
        while len(self.history) > 1 and (self._char_count / 4) > self.max_tokens:
            removed = self.history.pop(1)
            self._char_count -= len(removed.get("content", ""))

        # If single root message itself exceeds max_tokens, safely truncate root content
        if self.history and (len(self.history[0].get("content", "")) / 4) > self.max_tokens:
            max_chars = int(self.max_tokens * 4)
            old_len = len(self.history[0]["content"])
            self.history[0]["content"] = self.history[0]["content"][:max_chars]
            self._char_count -= (old_len - max_chars)

    def trim(self, max_turns: int = 10):
        """Trim working memory to max_turns while pinning the root user goal turn."""
        if len(self.history) > max_turns:
            root_msg = self.history[0]
            self.history = self.history[-max_turns:]
            if root_msg and root_msg not in self.history:
                self.history.insert(0, root_msg)
            # Recalculate char count after structural change
            self._char_count = sum(len(m.get("content", "")) for m in self.history)

    def get(self) -> list[dict]:
        return self.history

    def clear(self):
        """Clear all working memory history."""
        self.history.clear()
        self._char_count = 0

    def get_token_count(self) -> int:
        """Approximate token count (1 token ≈ 4 chars)."""
        return int(self._char_count / 4)
