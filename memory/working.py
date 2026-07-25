# memory/working.py

class WorkingMemory:
    def __init__(self, max_tokens: int = 100_000):
        self.history: list[dict] = []
        self.max_tokens = max_tokens

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self._trim()

    def _trim(self):
        # Rough token estimate: 1 token ~ 4 chars
        if not self.history:
            return

        total_chars = sum(len(m.get("content", "")) for m in self.history)
        if total_chars / 4 <= self.max_tokens:
            return

        root_msg = self.history[0]
        # Pop non-root turns (index 1) first to satisfy token budget
        while len(self.history) > 1 and (sum(len(m.get("content", "")) for m in self.history) / 4) > self.max_tokens:
            self.history.pop(1)

        # If single root message itself exceeds max_tokens, safely truncate root content
        if self.history and (len(self.history[0].get("content", "")) / 4) > self.max_tokens:
            max_chars = int(self.max_tokens * 4)
            self.history[0]["content"] = self.history[0]["content"][:max_chars]

    def trim(self, max_turns: int = 10):
        """Trim working memory to max_turns while pinning the root user goal turn."""
        if len(self.history) > max_turns:
            root_msg = self.history[0]
            self.history = self.history[-max_turns:]
            if root_msg and root_msg not in self.history:
                self.history.insert(0, root_msg)

    def get(self) -> list[dict]:
        return self.history
